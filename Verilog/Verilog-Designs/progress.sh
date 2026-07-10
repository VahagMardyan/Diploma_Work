dataset_part1="./Part1/dataset_power_part1.csv"
dataset_part2="./Part2/dataset_power_part2.csv"
dataset_part3="./Part3/dataset_power_part3.csv"
dataset_old_part2="../Verilog_New_Designs/dataset_power_small.csv"

echo "Part1:"
line1=$(wc -l < "$dataset_part1")

if [[ "$line1" -eq 24961 ]]; then
  echo "Done!"
else
  echo "$line1 out of 24961"
  echo "Last 5 lines: "
  tail -5 $dataset_part1
fi


echo "Part2:"
line2=$(wc -l < "$dataset_part2")

if [[ "$line2" -eq 36481 ]]; then
  echo "Done!"
else
  echo "$line2 out of 36481"
  echo "Last 5 lines: "
  tail -5 $dataset_part2
fi

echo "Part3:"
line3=$(wc -l < "$dataset_part3")

if [[ "$line3" -eq 49921 ]]; then
  echo "Done!"
else
  echo "$line3 out of 49921"
  echo "Last 5 lines: "
  tail -5 $dataset_part3
fi

echo "Verilog new Dataset"
line=$(wc -l < "$dataset_old_part2")
if [[ "$line" -eq 6481 ]]; then
  echo "Done!"
else
  echo "$line out of 6481"
  echo "Last 5 lines: "
  tail -5 $dataset_old_part2
fi