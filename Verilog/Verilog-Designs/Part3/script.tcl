set_host_options -max_cores 16

if {![info exists src_dir]} {
    set src_dir [pwd]
}

set out_file    "dataset_power_part3.csv"
set error_log   "synthesis_errors.log"
set checkpoint_file "completed_combos.log"

# ---------------------------------------------------------------------------
# CONFIG FLAGS
# ---------------------------------------------------------------------------
# per_freq_recompile = 1  -> compile_ultra is re-run for EACH target frequency
#                            (realistic: netlist structure depends on timing
#                            constraint, ~10x longer runtime)
# per_freq_recompile = 0  -> single compile_ultra at $synth_freq, then power
#                            is swept across freq_list without re-synthesis
#                            (fast, but dynamic_power vs freq becomes ~linear)
set per_freq_recompile 0

# Used only when per_freq_recompile = 0
set synth_freq 100.0

set freq_list {10 50 100 200 300 450 600 750 900 1000}

# ---------------------------------------------------------------------------
# Switching activity grid: 4 x 4 = 16 combinations (toggle_rate x static_prob)
# ---------------------------------------------------------------------------
set toggle_values {0.10 0.37 0.63 0.90}
set static_values  {0.10 0.37 0.63 0.90}

set switching_pairs {}
foreach t $toggle_values {
    foreach s $static_values {
        lappend switching_pairs [list $t $s]
    }
}

# PVT corners: library_name, vdd, temperature, process
set pvt_corners {
	{saed05rvt_base_tt0p60v25c 0.60 25 TT}
	{saed05rvt_base_tt0p60v125c 0.60 125 TT}
	{saed05rvt_base_tt0p75v125c 0.75 125 TT}
	{saed05rvt_base_tt0p75v25c 0.75 25 TT}

	{saed05rvt_base_ff0p660v125c 0.66 125 FF}
	{saed05rvt_base_ff0p660v25c 0.66 25 FF}
	{saed05rvt_base_ff0p825v125c 0.825 125 FF}
	{saed05rvt_base_ff0p825v25c 0.825 25 FF}

	{saed05rvt_base_ss0p540v125c 0.540 125 SS}
	{saed05rvt_base_ss0p540v25c 0.540 25 SS}
	{saed05rvt_base_ss0p675v125c 0.675 125 SS}
	{saed05rvt_base_ss0p675v25c 0.675 25 SS}
}

# ---------------------------------------------------------------------------
# RESUME SUPPORT
# ---------------------------------------------------------------------------
# If out_file already exists (previous session), keep appending to it instead
# of wiping it out. Only write the header the very first time.
if {![file exists $out_file]} {
    set out_fd [open $out_file w]
    puts $out_fd "design_name,clock_frequency_mhz,toggle_rate,static_probability,cell_count,seq_cell_count,total_area,logic_depth,dynamic_power,leakage_power,power_units,vdd,temperature,process,pvt_corner"
    close $out_fd
    echo "Started new dataset: $out_file"
} else {
    echo "Resuming existing dataset: $out_file (appending)"
}

# error_log is also appended across sessions instead of being wiped
if {![file exists $error_log]} {
    sh echo "" > $error_log
}

# Load the set of (design,corner,freq) triples that were already fully
# completed in a previous session, so we can skip them this time.
array set completed_set {}
if {[file exists $checkpoint_file]} {
    set cp_fd [open $checkpoint_file r]
    while {[gets $cp_fd line] >= 0} {
        set line [string trim $line]
        if {$line ne ""} {
            set completed_set($line) 1
        }
    }
    close $cp_fd
    echo "Loaded [array size completed_set] completed (design,corner,freq) combos from checkpoint"
}

proc mark_combo_done {checkpoint_file design corner freq} {
    set cp_fd [open $checkpoint_file a]
    puts $cp_fd "$design,$corner,$freq"
    close $cp_fd
}

set all_v_files [glob -nocomplain "$src_dir/*/*.v" "$src_dir/*.v"]

proc is_skipped_file {filepath} {
    set base [string tolower [file rootname [file tail $filepath]]]
    if {[string match "*tb*" $base]} { return 1 }
    if {$base eq "half_adder_pipe"} { return 1 }
    return 0
}

proc get_seq_cell_count {} {
    set seq_count 0

    set regs [all_registers]
    if {![catch {sizeof_collection $regs} cnt] && $cnt > 0} {
        return $cnt
    }

    set area_txt ""
    if {![catch {redirect -variable area_txt {report_area}}]} {
        foreach line [split $area_txt "\n"] {
            if {[regexp {Number of sequential cells:\s*([0-9]+)} $line -> val]} {
                set seq_count $val
                break
            }
        }
    }

    if {$seq_count eq ""} { set seq_count 0 }
    return $seq_count
}

proc apply_switching_activity {toggle_rate static_prob} {
    foreach_in_collection port [all_inputs] {
        catch {set_switching_activity -toggle $toggle_rate -static $static_prob $port}
    }
    catch {propagate_switching_activity}
}

proc get_total_area {} {
    set total_area 0.0
    set area_txt ""
    if {![catch {redirect -variable area_txt {report_area}}]} {
        foreach line [split $area_txt "\n"] {
            if {[regexp {Total cell area:\s*([0-9.eE+\-]+)} $line -> val]} {
                set total_area $val
                break
            }
        }
    }
    return $total_area
}

proc get_logic_depth {} {
    set logic_depth 0
    if {![catch {set paths [get_timing_paths -max_paths 1 -nworst 1]}]} {
        if {[sizeof_collection $paths] > 0} {
            set points [get_attribute [index_collection $paths 0] points]
            if {![catch {set n [sizeof_collection $points]}] && $n >= 2} {
                set logic_depth [expr {$n - 2}]
            }
        }
    }
    if {$logic_depth < 0} { set logic_depth 0 }
    return $logic_depth
}

proc get_power_values {} {
    set dynamic_val 0.0
    set leakage_val 0.0
    set dynamic_unit "nW"
    set leakage_unit "pW"
    set power_txt ""
    if {![catch {redirect -variable power_txt {report_power}}]} {
    	foreach line [split $power_txt "\n"] {
    		if {[regexp {Total Dynamic Power\s*=\s*([0-9.eE+\-]+)\s*([a-zA-Z]+)} $line -> val unit]} {
    			set dynamic_val $val
    			set dynamic_unit $unit
    		}
    		if {[regexp {Cell Leakage Power\s*=\s*([0-9.eE+\-]+)\s*([a-zA-Z]+)} $line -> val unit]} {
    			set leakage_val $val
    			set leakage_unit $unit
    		}
    	}
    }
    return [list $dynamic_val $leakage_val $dynamic_unit $leakage_unit]
}

# Collect and log the static (structural) metrics for the currently
# elaborated/compiled design. Called once per (design, corner) when
# per_freq_recompile=0, or once per (design, corner, freq) when =1.
proc collect_static_metrics {} {
    if {[catch {set cell_count [sizeof_collection [get_cells -hierarchical]]} _]} {
        set cell_count 0
    }
    if {$cell_count eq ""} { set cell_count 0 }

    set seq_count   [get_seq_cell_count]
    set total_area  [get_total_area]
    set logic_depth [get_logic_depth]

    return [list $cell_count $seq_count $total_area $logic_depth]
}

foreach f $all_v_files {
    if {[is_skipped_file $f]} {
        echo "Skipping: [file tail $f]"
        continue
    }

    set design_name [file rootname [file tail $f]]

    echo "Processing: $design_name"
    echo "File: $f"

    foreach corner $pvt_corners {
        set library_basename [lindex $corner 0]
        set vdd_val          [lindex $corner 1]
        set temp_val         [lindex $corner 2]
        set process_val      [lindex $corner 3]

        echo "  --> PVT: $library_basename (Vdd=$vdd_val, T=$temp_val, $process_val)"

        catch {remove_design -all}

        if {[catch {read_verilog $f} read_err]} {
            set msg "READ ERROR - $read_err"
            echo "ERROR: $msg"
            sh echo "$design_name,$library_basename: $msg" >> $error_log
            continue
        }

        if {[catch {current_design $design_name} cd_err]} {
            set msg "CURRENT_DESIGN ERROR - $cd_err"
            echo "ERROR: $msg"
            sh echo "$design_name,$library_basename: $msg" >> $error_log
            continue
        }

        if {[catch {link} link_err]} {
            echo "ERROR: LINK ERROR - $link_err"
            sh echo "$design_name,$library_basename: LINK ERROR - $link_err" >> $error_log
            continue
        }

        set lib_path "/remote/exchange/synopsys/SAED05_EDK/SAED05nm_EDK_STD_RVT/liberty/nldm/base/${library_basename}.db"

        if {![file exists $lib_path]} {
            set error_msg "LIBRARY NOT FOUND: $lib_path"
            echo "ERROR: $error_msg"
            sh echo "$design_name,$library_basename: $error_msg" >> $error_log
            continue
        }
        set target_library $lib_path
        set link_library "* $lib_path"
        catch {set_operating_conditions $library_basename -library $library_basename}

        # Check cells after link
        if {[catch {set cell_count_temp [sizeof_collection [get_cells -hierarchical]]} _]} {
            set cell_count_temp 0
        }
        if {$cell_count_temp == 0} {
            sh echo "$design_name,$library_basename: SKIPPED - 0 cells after link" >> $error_log
            continue
        }

        if {!$per_freq_recompile} {
            # ---- Original behaviour: ONE compile at fixed synth_freq ----
            set period [expr {1000.0 / $synth_freq}]
            catch {remove_clock [all_clocks]}
            catch {create_clock -name vclk -period $period}
            catch {set_input_delay  -clock vclk 0 [all_inputs]}
            catch {set_output_delay -clock vclk 0 [all_outputs]}

            if {[catch {compile_ultra} synth_err]} {
                echo "ERROR: SYNTH ERROR - $synth_err"
                sh echo "$design_name,$library_basename: SYNTH ERROR - $synth_err" >> $error_log
                continue
            }

            set metrics    [collect_static_metrics]
            set cell_count [lindex $metrics 0]
            set seq_count  [lindex $metrics 1]
            set total_area [lindex $metrics 2]
            set logic_depth [lindex $metrics 3]

            echo "  cell_count=$cell_count seq_cell_count=$seq_count area=$total_area depth=$logic_depth"
        }

        # Frequency sweep
        foreach freq $freq_list {

            # ---- CHECKPOINT: skip if this (design,corner,freq) was already
            # ---- fully completed in a previous session ----
            set combo_key "$design_name,$library_basename,$freq"
            if {[info exists completed_set($combo_key)]} {
                echo "  [skip] already completed: $combo_key"
                continue
            }

            set period [expr {1000.0 / $freq}]

            if {$per_freq_recompile} {
                # ---- Re-read/re-link/re-compile for THIS target frequency ----
                catch {remove_design -all}
                if {[catch {read_verilog $f} read_err]} {
                    sh echo "$design_name,$library_basename,freq=$freq: READ ERROR - $read_err" >> $error_log
                    continue
                }
                if {[catch {current_design $design_name} cd_err]} {
                    sh echo "$design_name,$library_basename,freq=$freq: CURRENT_DESIGN ERROR - $cd_err" >> $error_log
                    continue
                }
                if {[catch {link} link_err]} {
                    sh echo "$design_name,$library_basename,freq=$freq: LINK ERROR - $link_err" >> $error_log
                    continue
                }
                catch {set_operating_conditions $library_basename -library $library_basename}

                catch {remove_clock [all_clocks]}
                catch {create_clock -name vclk -period $period}
                catch {set_input_delay  -clock vclk 0 [all_inputs]}
                catch {set_output_delay -clock vclk 0 [all_outputs]}

                if {[catch {compile_ultra} synth_err]} {
                    echo "ERROR: SYNTH ERROR (freq=$freq) - $synth_err"
                    sh echo "$design_name,$library_basename,freq=$freq: SYNTH ERROR - $synth_err" >> $error_log
                    continue
                }

                set metrics    [collect_static_metrics]
                set cell_count [lindex $metrics 0]
                set seq_count  [lindex $metrics 1]
                set total_area [lindex $metrics 2]
                set logic_depth [lindex $metrics 3]

                echo "  [freq=$freq MHz] cell_count=$cell_count seq_cell_count=$seq_count area=$total_area depth=$logic_depth"
            } else {
                # Netlist already compiled once; just re-apply the clock
                # period so timing-based reports (e.g. logic depth) still
                # refer to the correct constraint context.
                catch {remove_clock [all_clocks]}
                catch {create_clock -name vclk -period $period}
                catch {set_input_delay  -clock vclk 0 [all_inputs]}
                catch {set_output_delay -clock vclk 0 [all_outputs]}
            }

            foreach pair $switching_pairs {
                set toggle_rate [lindex $pair 0]
                set static_prob [lindex $pair 1]

                apply_switching_activity $toggle_rate $static_prob

                set power_vals  [get_power_values]
                set dynamic_val [lindex $power_vals 0]
                set leakage_val [lindex $power_vals 1]
                set dynamic_unit [lindex $power_vals 2]
                set leakage_unit [lindex $power_vals 3]
                set power_units "${dynamic_unit}/${leakage_unit}"

                # Append to CSV with PVT data
                set out_fd [open $out_file a]
                puts $out_fd "$design_name,$freq,$toggle_rate,$static_prob,$cell_count,$seq_count,$total_area,$logic_depth,$dynamic_val,$leakage_val,$power_units,$vdd_val,$temp_val,$process_val,$library_basename"
                close $out_fd

                echo "  --> freq=$freq MHz tr=$toggle_rate sp=$static_prob : dyn=$dynamic_val leak=$leakage_val Vdd=$vdd_val T=$temp_val"
            }

            # ---- CHECKPOINT: mark this (design,corner,freq) as fully done ----
            mark_combo_done $checkpoint_file $design_name $library_basename $freq
        }

        echo "  Finished PVT: $library_basename"
    }
    # end of PVT corner loop ^

    echo "Finished processing $design_name"
    echo ""
}

echo "COMPLETE! Dataset has written to '$out_file'"
echo "Errors logged to '$error_log'"