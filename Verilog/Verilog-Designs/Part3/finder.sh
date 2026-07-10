modules=("mux_condt" "mux_always" "mux_case" "univ_shift" "no_1s" "half_adder" "pipeline" "rca16b" "rca32b" "rca64" "rca8b" "rca_4b" "rca_4b1" "vdcmul_16b" "vdcmul_2b" "vdcmul_32b" "vdcmul_4b" "vdcmul_64b" "vdcmul_8b" "priority_encoder_8to3" "seqmult" "shift_reg_16bit" "singleport_ram" "dff_sync" "syncfifo")

target_file="./dataset_power_part3.csv"

for term in "${modules[@]}"; do
	count=$(grep -c "$term" "$target_file")
	echo "$term : $count"
done