# Design Compiler version: W-2024.09SP3

set_host_options -max_cores 16

# Directories and files
if {![info exists src_dir]} {
    set src_dir [pwd]
}

set out_file        "dataset_power_test_encoder.csv"
set error_log       "synthesis_errors_test_encoder.log"
set checkpoint_file "completed_combos_test_encoder.log"

# Synthesis configuration
set per_freq_recompile 0
set synth_freq 100.0

# Frequency list (MHz)
set freq_list { 15 60 120 250 400 670 850 1000 }

# SWITCHING ACTIVITY CONFIGURATION
set toggle_values { 0.07 0.25 0.50 0.75 0.95 }
set static_values { 0.05 0.3 0.65 0.8 0.95 }

set switching_pairs {}
foreach t $toggle_values {
    foreach s $static_values {
        lappend switching_pairs [list $t $s]
    }
}

# PVT corners (SAED05)
set lib_base "/remote/exchange/synopsys/SAED05_EDK/SAED05nm_EDK_STD_RVT/liberty/nldm/base"

set pvt_corners {
    {saed05rvt_base_tt0p60v25c   0.60 25  TT}
    {saed05rvt_base_tt0p60v125c  0.60 125 TT}
    {saed05rvt_base_tt0p75v25c   0.75 25  TT}
    {saed05rvt_base_tt0p75v125c  0.75 125 TT}
    {saed05rvt_base_ff0p660v25c  0.660 25  FF}
    {saed05rvt_base_ff0p660v125c 0.660 125 FF}
    {saed05rvt_base_ff0p825v25c  0.825 25  FF}
    {saed05rvt_base_ff0p825v125c 0.825 125 FF}
    {saed05rvt_base_ss0p540v25c  0.540 25  SS}
    {saed05rvt_base_ss0p540v125c 0.540 125 SS}
    {saed05rvt_base_ss0p675v25c  0.675 25  SS}
    {saed05rvt_base_ss0p675v125c 0.675 125 SS}
}

# --------------------------------------------------------------------------
# Library setup
# --------------------------------------------------------------------------
proc setup_library {lib_base library_name} {
    global target_library link_library
    set lib_path "${lib_base}/${library_name}.db"
    if {![file exists $lib_path]} {
        puts "ERROR: Library not found: $lib_path"
        return 0
    }
    set target_library [list $lib_path]
    set link_library [list "*" $lib_path]
    if {[catch {set_operating_conditions $library_name -library $library_name} err]} {
        puts "WARNING: Could not set operating conditions: $err"
    }
    return 1
}

# --------------------------------------------------------------------------
# Helper procedures
# --------------------------------------------------------------------------
proc log_error {error_log design corner freq msg} {
    set fd [open $error_log a]
    puts $fd "\[[clock format [clock seconds] -format {%Y-%m-%d %H:%M:%S}]\] design=$design corner=$corner freq=$freq :: $msg"
    close $fd
    echo "ERROR: $msg"
}

proc safe_remove_all_clocks {} {
    if {[sizeof_collection [all_clocks]] > 0} {
        catch {remove_clock [all_clocks]}
    }
}

proc mark_combo_done {checkpoint_file design corner freq} {
    set cp_fd [open $checkpoint_file a]
    puts $cp_fd "$design,$corner,$freq"
    close $cp_fd
}

# --------------------------------------------------------------------------
# CSV header (without capacitance)
# --------------------------------------------------------------------------
if {![file exists $out_file]} {
    set out_fd [open $out_file w]
    set header_fields {
        design_name clock_frequency_mhz toggle_rate static_probability
        cell_count comb_cell_count seq_cell_count
        inv_count buf_count nand_count nor_count xor_count mux_count other_count
        total_area avg_cell_area
        num_nets num_inputs num_outputs
        max_fanout avg_fanout avg_fanin
        logic_depth depth_mean depth_std depth_max
        critical_path_delay wns tns
        avg_net_toggle toggle_attenuation
        dynamic_power_uW leakage_power_uW total_power_uW
        vdd temperature process pvt_corner
    }
    puts $out_fd [join $header_fields ","]
    close $out_fd
    echo "Created new dataset: $out_file"
} else {
    echo "Resuming existing dataset: $out_file"
}

if {![file exists $error_log]} {
    sh echo "" > $error_log
}

# Checkpoint handling
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
    echo "Loaded [array size completed_set] completed combinations"
}

# --------------------------------------------------------------------------
# Find Verilog files
# --------------------------------------------------------------------------
set all_v_files [glob -nocomplain "$src_dir/*.v" "$src_dir/*/*.v" "$src_dir/*/*/*.v"]
echo "Found [llength $all_v_files] Verilog files"

proc is_skipped_file {filepath} {
    set base [string tolower [file rootname [file tail $filepath]]]
    if {[string match "*tb*" $base]} { return 1 }
    if {$base eq "half_adder_pipe"} { return 1 }
    if {$base eq "mux_condt"} { return 1 }
    if {$base eq "full_half_adder_1bit"} { return 1 }
    if {$base eq "full_half_add_1bit"} { return 1 }
    return 0
}

# --------------------------------------------------------------------------
# Extraction functions (only essential data)
# --------------------------------------------------------------------------

proc apply_switching_activity {toggle_rate static_prob} {
    foreach_in_collection port [all_inputs] {
        catch { set_switching_activity -toggle $toggle_rate -static $static_prob $port }
    }
    catch { propagate_switching_activity }
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

proc get_avg_cell_area {area count} {
    if {$count == 0} { return 0.0 }
    return [expr {$area / double($count)}]
}

proc classify_cell_token {tok} {
    switch -exact -- $tok {
        DFF - SDFF - DF - SDF - FD - SCAN - LATCH - DLAT - DL { return "SEQ" }
        INV - IV - IVX - CLKINV { return "INV" }
        BUF - BF - BFX - CLKBUF { return "BUF" }
        NAND - ND { return "NAND" }
        NOR - NR { return "NOR" }
        XOR - XO - XOR2 { return "XOR" }
        XNOR - XNR - XOR2N { return "XOR" }
        MUX - MX - MUX2 { return "MUX" }
        AOI - AO { return "MUX" }
        OAI - OA { return "MUX" }
        AND - AN { return "AND" }
        OR - OR2 { return "OR" }
        default { return "" }
    }
}

proc get_cell_statistics {{debug_log ""}} {
    array set counts { INV 0 BUF 0 NAND 0 NOR 0 XOR 0 MUX 0 AND 0 OR 0 OTHER 0 SEQ 0 }
    set cells [get_cells -hierarchical]
    set total [sizeof_collection $cells]

    foreach_in_collection cell $cells {
        if {[catch {set ref [get_attribute $cell ref_name]}]} { continue }
        set ref_upper [string toupper $ref]
        set category ""

        foreach tok [split $ref_upper "_"] {
            set hit [classify_cell_token $tok]
            if {$hit eq "" } {
                set stripped [regsub {[0-9]+$} $tok ""]
                if {$stripped ne $tok} { set hit [classify_cell_token $stripped] }
            }
            if {$hit ne ""} { set category $hit; break }
        }

        if {$category eq ""} {
            if {[regexp {^(DFF|SDFF|SCAN|LATCH|DLAT)} $ref_upper]} { set category "SEQ" }
            if {[regexp {^(INV|CLKINV)} $ref_upper]} { set category "INV" }
            if {[regexp {^(BUF|CLKBUF)} $ref_upper]} { set category "BUF" }
            if {[regexp {^NAND} $ref_upper]} { set category "NAND" }
            if {[regexp {^NOR} $ref_upper]} { set category "NOR" }
            if {[regexp {^(XNOR|XOR)} $ref_upper]} { set category "XOR" }
            if {[regexp {^(MUX|AOI|OAI)} $ref_upper]} { set category "MUX" }
            if {[regexp {^AND} $ref_upper]} { set category "AND" }
            if {[regexp {^OR} $ref_upper]} { set category "OR" }
        }

        switch -exact -- $category {
            SEQ  { incr counts(SEQ) }
            INV  { incr counts(INV) }
            BUF  { incr counts(BUF) }
            NAND { incr counts(NAND) }
            NOR  { incr counts(NOR) }
            XOR  { incr counts(XOR) }
            MUX  { incr counts(MUX) }
            AND  { incr counts(AND) }
            OR   { incr counts(OR) }
            default { incr counts(OTHER) }
        }
    }

    set comb_count [expr {$total - $counts(SEQ)}]
    set other_total [expr {$counts(OTHER) + $counts(AND) + $counts(OR)}]
    return [list $total $comb_count $counts(SEQ) $counts(INV) $counts(BUF) $counts(NAND) $counts(NOR) $counts(XOR) $counts(MUX) $other_total]
}

proc get_net_statistics {} {
    set nets [get_nets -hierarchical]
    set num_nets [sizeof_collection $nets]
    set inputs 0
    set outputs 0
    if {[catch {set ports [get_ports *]}]} { catch {set ports [all_ports]} }
    foreach_in_collection p $ports {
        set dir [get_attribute $p direction]
        if {$dir eq "in"}  { incr inputs }
        if {$dir eq "out"} { incr outputs }
    }
    return [list $num_nets $inputs $outputs]
}

proc get_fanout_fanin_stats {} {
    set fanouts {}
    set total_fanin 0.0
    set cells [get_cells -hierarchical]
    set cell_count [sizeof_collection $cells]
    if {$cell_count == 0} { return [list 0 0 0] }

    foreach_in_collection cell $cells {
        set out_pins [get_pins -of_object $cell -filter "direction==out"]
        if {[sizeof_collection $out_pins] > 0} {
            if {![catch {set fan [sizeof_collection [all_fanout -from $out_pins -flat]]}]} {
                lappend fanouts $fan
            }
        }
        set in_pins [get_pins -of_object $cell -filter "direction==in"]
        set total_fanin [expr {$total_fanin + [sizeof_collection $in_pins]}]
    }

    set avg_fanin [expr {$total_fanin / double($cell_count)}]
    if {[llength $fanouts] == 0} {
        return [list 0 0 $avg_fanin]
    }

    set max_fanout [lindex [lsort -real $fanouts] end]
    set avg_fanout 0.0
    foreach f $fanouts { set avg_fanout [expr {$avg_fanout + $f}] }
    set avg_fanout [expr {$avg_fanout / double([llength $fanouts])}]

    return [list $max_fanout $avg_fanout $avg_fanin]
}

proc get_timing_metrics {} {
    set wns 0.0; set tns 0.0; set critical_delay 0.0; set timing_txt ""
    if {![catch {redirect -variable timing_txt {report_timing -max_paths 1 -delay_type max}}]} {
        foreach line [split $timing_txt "\n"] {
            if {[regexp {slack\s*\(MET\)\s*([\-0-9.eE+]+)} $line -> val]} { set wns $val }
            if {[regexp {data arrival time\s*([0-9.eE+]+)} $line -> val]} { set critical_delay $val }
        }
    }
    set constraint_txt ""
    if {![catch {redirect -variable constraint_txt {report_constraint -all_violators}}]} {
        foreach line [split $constraint_txt "\n"] {
            if {[regexp {Total Negative Slack\s*([\-0-9.eE+]+)} $line -> val]} { set tns $val }
        }
    }
    return [list $wns $tns $critical_delay]
}

proc get_logic_depth {} {
    set depth 0
    if {![catch {set paths [get_timing_paths -max_paths 1 -nworst 1]}]} {
        if {[sizeof_collection $paths] > 0} {
            set points [get_attribute [index_collection $paths 0] points]
            set count [sizeof_collection $points]
            set depth [expr {$count - 2}]
        }
    }
    if {$depth < 0} { set depth 0 }
    return $depth
}

proc get_depth_distribution {number_of_paths} {
    set depths {}
    if {[catch {set paths [get_timing_paths -max_paths $number_of_paths]}]} {
        return [list 0 0 0]
    }
    set count [sizeof_collection $paths]
    for {set i 0} {$i < $count} {incr i} {
        set path [index_collection $paths $i]
        if {[catch {set points [get_attribute $path points]}]} { continue }
        set d [expr {[sizeof_collection $points] - 2}]
        if {$d < 0} { set d 0 }
        lappend depths $d
    }
    if {[llength $depths] == 0} { return [list 0 0 0] }

    set sum 0.0
    foreach d $depths { set sum [expr {$sum + $d}] }
    set mean [expr {$sum / double([llength $depths])}]

    set variance 0.0
    foreach d $depths {
        set diff [expr {$d - $mean}]
        set variance [expr {$variance + $diff * $diff}]
    }
    set std [expr {sqrt($variance / double([llength $depths]))}]
    set max [lindex [lsort -integer $depths] end]

    return [list $mean $std $max]
}

proc get_net_activity {net} {
    if {![catch {set a [get_attribute $net switching_activity]}]} { return $a }
    if {![catch {set a [get_attribute $net toggle_rate]}]} { return $a }
    return 0.0
}

proc get_activity_statistics {} {
    set total 0.0; set count 0
    foreach_in_collection net [get_nets -hierarchical] {
        set act [get_net_activity $net]
        set total [expr {$total + $act}]
        incr count
    }
    if {$count == 0} { return 0.0 }
    return [expr {$total / double($count)}]
}

proc normalize_to_uw {value unit} {
    set unit [string tolower [string trim $unit]]
    switch $unit {
        "mw" { return [expr {$value * 1000.0}] }
        "uw" { return $value }
        "nw" { return [expr {$value / 1000.0}] }
        "pw" { return [expr {$value / 1000000.0}] }
    }
    return $value
}

proc get_power_values {} {
    set dynamic 0.0; set leakage 0.0; set total 0.0; set txt ""
    if {![catch {redirect -variable txt {report_power}}]} {
        foreach line [split $txt "\n"] {
            if {[regexp {Total Dynamic Power\s*=\s*([0-9.eE+\-]+)\s*([a-zA-Z]+)} $line -> val unit]} {
                set dynamic [normalize_to_uw $val $unit]
            }
            if {[regexp {Cell Leakage Power\s*=\s*([0-9.eE+\-]+)\s*([a-zA-Z]+)} $line -> val unit]} {
                set leakage [normalize_to_uw $val $unit]
            }
            if {[regexp {Total Power\s*=\s*([0-9.eE+\-]+)\s*([a-zA-Z]+)} $line -> val unit]} {
                set total [normalize_to_uw $val $unit]
            }
        }
    }
    if {$total == 0.0} { set total [expr {$dynamic + $leakage}] }
    return [list $dynamic $leakage $total]
}

# --------------------------------------------------------------------------
# Main loop
# --------------------------------------------------------------------------
set design_count 0
set total_designs [llength $all_v_files]

foreach verilog_file $all_v_files {
    if {[is_skipped_file $verilog_file]} {
        echo "Skipping [file tail $verilog_file]"
        continue
    }

    set design_name [file rootname [file tail $verilog_file]]
    incr design_count

    echo "========================================"
    echo "Processing $design_name ($design_count/$total_designs)"

    foreach corner $pvt_corners {
        set library_name [lindex $corner 0]
        set vdd_val      [lindex $corner 1]
        set temp_val     [lindex $corner 2]
        set process_val  [lindex $corner 3]

        echo "PVT: $library_name"
        catch {remove_design -all}

        if {![setup_library $lib_base $library_name]} {
            log_error $error_log $design_name $library_name "-" "Failed to setup library: $library_name"
            continue
        }

        if {[catch {read_verilog $verilog_file} errmsg]} {
            log_error $error_log $design_name $library_name "-" "read_verilog failed: $errmsg"
            continue
        }

        if {[catch {current_design $design_name} errmsg]} {
            set found_designs ""
            catch {set found_designs [get_designs -quiet *]}
            log_error $error_log $design_name $library_name "-" "current_design failed: $errmsg (designs in memory: $found_designs)"
            continue
        }

        if {[catch {link} errmsg]} {
            log_error $error_log $design_name $library_name "-" "link failed: $errmsg"
            continue
        }

        if {!$per_freq_recompile} {
            set period [expr {1000.0 / $synth_freq}]
            safe_remove_all_clocks
            create_clock -name vclk -period $period
            set_input_delay -clock vclk 0 [all_inputs]
            set_output_delay -clock vclk 0 [all_outputs]

            if {[catch {compile_ultra} errmsg]} {
                log_error $error_log $design_name $library_name $synth_freq "compile_ultra failed: $errmsg"
                continue
            }
        }

        # Extract static features (once per corner)
        set cell_stats [get_cell_statistics $error_log]
        set cell_count      [lindex $cell_stats 0]
        set comb_cell_count [lindex $cell_stats 1]
        set seq_cell_count  [lindex $cell_stats 2]
        set inv_count       [lindex $cell_stats 3]
        set buf_count       [lindex $cell_stats 4]
        set nand_count      [lindex $cell_stats 5]
        set nor_count       [lindex $cell_stats 6]
        set xor_count       [lindex $cell_stats 7]
        set mux_count       [lindex $cell_stats 8]
        set other_count     [lindex $cell_stats 9]

        set total_area           [get_total_area]
        set avg_cell_area        [get_avg_cell_area $total_area $cell_count]

        set net_stats   [get_net_statistics]
        set num_nets    [lindex $net_stats 0]
        set num_inputs  [lindex $net_stats 1]
        set num_outputs [lindex $net_stats 2]

        set fan_stats  [get_fanout_fanin_stats]
        set max_fanout [lindex $fan_stats 0]
        set avg_fanout [lindex $fan_stats 1]
        set avg_fanin  [lindex $fan_stats 2]

        set logic_depth [get_logic_depth]
        set depth_stats [get_depth_distribution 20]
        set depth_mean  [lindex $depth_stats 0]
        set depth_std   [lindex $depth_stats 1]
        set depth_max   [lindex $depth_stats 2]

        set timing_stats        [get_timing_metrics]
        set wns                 [lindex $timing_stats 0]
        set tns                 [lindex $timing_stats 1]
        set critical_path_delay [lindex $timing_stats 2]

        # Frequency loop
        foreach freq $freq_list {
            set combo_key "$design_name,$library_name,$freq"
            if {[info exists completed_set($combo_key)]} {
                echo "Skipping already-completed combo: $combo_key"
                continue
            }

            set period [expr {1000.0 / $freq}]
            safe_remove_all_clocks
            create_clock -name vclk -period $period

            foreach pair $switching_pairs {
                set toggle_rate        [lindex $pair 0]
                set static_probability [lindex $pair 1]

                apply_switching_activity $toggle_rate $static_probability

                set power [get_power_values]
                set dynamic_power_uW [lindex $power 0]
                set leakage_power_uW [lindex $power 1]
                set total_power_uW   [lindex $power 2]

                set avg_net_toggle [get_activity_statistics]
                if {$toggle_rate > 0} {
                    set toggle_attenuation [expr {$avg_net_toggle / $toggle_rate}]
                } else {
                    set toggle_attenuation 0
                }

                # Write row (without capacitance)
                set row_data [list \
                    $design_name $freq $toggle_rate $static_probability \
                    $cell_count $comb_cell_count $seq_cell_count \
                    $inv_count $buf_count $nand_count $nor_count $xor_count $mux_count $other_count \
                    $total_area $avg_cell_area \
                    $num_nets $num_inputs $num_outputs \
                    $max_fanout $avg_fanout $avg_fanin \
                    $logic_depth $depth_mean $depth_std $depth_max \
                    $critical_path_delay $wns $tns \
                    $avg_net_toggle $toggle_attenuation \
                    $dynamic_power_uW $leakage_power_uW $total_power_uW \
                    $vdd_val $temp_val $process_val $library_name \
                ]

                set fd [open $out_file a]
                puts $fd [join $row_data ","]
                close $fd
                echo "Wrote row for $design_name @ $freq MHz (toggle=$toggle_rate, static=$static_probability)"
            }
            mark_combo_done $checkpoint_file $design_name $library_name $freq
        }
        echo "Finished corner $library_name"
    }
    echo "Finished design $design_name"
}

echo "========================================"
echo "DATASET GENERATION COMPLETE"
echo "Output: $out_file"
echo "Designs processed: $design_count"
echo "See $error_log for errors"
echo "========================================"