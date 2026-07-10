remove_design -all
read_verilog ./1_bit_Full_Adder_using_HA/full_half_add_1bit.v
current_design full_half_add_bit
link

set target_library "/remote/exchange/synopsys/SAED05_EDK/SAED05nm_EDK_STD_RVT/liberty/nldm/base/saed05rvt_base_tt0p60v125c.db"
set link_library "/remote/exchange/synopsys/SAED05_EDK/SAED05nm_EDK_STD_RVT/liberty/nldm/base/saed05rvt_base_tt0p60v125c.db"

create_clock -name vclk -period 10
set_input_delay -clock vclk 0 [all_inputs]
set_output_delay -clock vclk 0 [all_outputs]

compile_ultra

echo "=============================Power without switching==========================="
report_power

echo "=============================Power with toggle=0.1============================="
set_switching_activity -toggle 0.1 -static 0.5 [all_inputs]
propagate_switching_activity
report_power

echo "=============================Power with toggle=0.5============================="
set_switching_activity -toggle 0.5 -static 0.5 [all_inputs]
propagate_switching_activity
report_power

echo "============================Power with toggle=0.8=============================="
set_switching_activity -toggle 0.8 -static 0.5 [all_inputs]
propagate_switching_activity
report_power

