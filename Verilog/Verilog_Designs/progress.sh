#!/bin/bash

# Color codes for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Expected row counts (excluding header = 1 row)
# Old dataset: 10 freq × 16 pairs × 12 PVT = 1920 rows per design
# New dataset: 8 freq × 25 pairs × 12 PVT = 2400 rows per design

# Part1 - 12 designs
PART1_1_OLD=9600
PART1_1_NEW=7680
PART1_2_OLD=9600
PART1_2_NEW=7680
PART1_3_OLD=9600
PART1_3_NEW=7680
PART1_OLD_TOTAL=28800
PART1_NEW_TOTAL=23040

# Part2 - 19 designs
PART2_1_OLD=24000
PART2_1_NEW=19200
PART2_2_OLD=9600
PART2_2_NEW=7680
PART2_3_OLD=12000
PART2_3_NEW=9600
PART2_OLD_TOTAL=45600
PART2_NEW_TOTAL=36480

# Part3 - 23 designs
PART3_1_OLD=9600
PART3_1_NEW=7680
PART3_2_OLD=36000
PART3_2_NEW=28800
PART3_3_OLD=9600
PART3_3_NEW=7680
PART3_OLD_TOTAL=55200
PART3_NEW_TOTAL=44160

# Part4 - 10 designs (no sub-parts)
PART4_OLD=24000
PART4_NEW=19200

# Function to check a CSV file
# Returns: line count (excluding header) or 0 if file doesn't exist
check_file() {
    local file="$1"
    if [[ -f "$file" ]]; then
        local lines=$(wc -l < "$file" 2>/dev/null | tr -d ' ')
        if [[ "$lines" -gt 0 ]]; then
            echo $((lines - 1))
        else
            echo 0
        fi
    else
        echo 0
    fi
}

# Function to check a sub-part
check_subpart() {
    local name="$1"
    local old_file="$2"
    local new_file="$3"
    local old_expected="$4"
    local new_expected="$5"
    
    local old_count=$(check_file "$old_file")
    local new_count=$(check_file "$new_file")
    
    local old_done=""
    local new_done=""
    local sub_done=""
    
    if [[ "$old_count" -eq "$old_expected" ]] && [[ "$old_expected" -gt 0 ]]; then
        old_done="${GREEN}✓${NC}"
    else
        old_done="${RED}✗${NC}"
    fi
    
    if [[ "$new_count" -eq "$new_expected" ]] && [[ "$new_expected" -gt 0 ]]; then
        new_done="${GREEN}✓${NC}"
    else
        new_done="${RED}✗${NC}"
    fi
    
    if [[ "$old_count" -eq "$old_expected" ]] && [[ "$new_count" -eq "$new_expected" ]]; then
        sub_done="${GREEN}DONE${NC}"
    else
        sub_done="${YELLOW}PENDING${NC}"
    fi
    
    # Use echo -e to interpret color codes
    echo -e "  ${name} | ${old_done} Old: ${old_count}/${old_expected} | ${new_done} New: ${new_count}/${new_expected} | ${sub_done}"
    
    if [[ "$old_count" -eq "$old_expected" ]] && [[ "$new_count" -eq "$new_expected" ]]; then
        return 0
    else
        return 1
    fi
}

# Function to check a full Part
check_part() {
    local part_name="$1"
    shift
    local total_old=0
    local total_new=0
    local all_done=1
    
    echo ""
    echo "=========================================="
    echo "$part_name"
    echo "=========================================="
    
    while [[ $# -gt 0 ]]; do
        local name="$1"
        local old_file="$2"
        local new_file="$3"
        local old_exp="$4"
        local new_exp="$5"
        shift 5
        
        check_subpart "$name" "$old_file" "$new_file" "$old_exp" "$new_exp"
        if [[ $? -ne 0 ]]; then
            all_done=0
        fi
        total_old=$((total_old + old_exp))
        total_new=$((total_new + new_exp))
    done
    
    if [[ $all_done -eq 1 ]]; then
        echo -e "${GREEN}$part_name COMPLETE!${NC} (Old: $total_old rows, New: $total_new rows)"
    else
        echo -e "${YELLOW}$part_name IN PROGRESS${NC} (Old: $total_old rows, New: $total_new rows total)"
    fi
}

# MAIN EXECUTION

echo ""
echo "==========================================================================="
echo "DATASET GENERATION PROGRESS MONITOR"
echo "==========================================================================="
echo ""
echo -e "  ${BLUE}Legend:${NC} ${GREEN}✓${NC} = Complete  ${RED}✗${NC} = Incomplete"
echo ""

# Part1
check_part "Part1" \
    "Part1_1" "./Part1/Part1_1/dataset_power_part1_1.csv" \
               "./Part1/Part1_1/dataset_power_alt_part1_1.csv" \
               "$PART1_1_OLD" "$PART1_1_NEW" \
    "Part1_2" "./Part1/Part1_2/dataset_power_part1_2.csv" \
               "./Part1/Part1_2/dataset_power_alt_part1_2.csv" \
               "$PART1_2_OLD" "$PART1_2_NEW" \
    "Part1_3" "./Part1/Part1_3/dataset_power_part1_3.csv" \
               "./Part1/Part1_3/dataset_power_alt_part1_3.csv" \
               "$PART1_3_OLD" "$PART1_3_NEW"

# Part2
check_part "Part2" \
    "Part2_1" "./Part2/Part2_1/dataset_power_part2_1.csv" \
               "./Part2/Part2_1/dataset_power_alt_part2_1.csv" \
               "$PART2_1_OLD" "$PART2_1_NEW" \
    "Part2_2" "./Part2/Part2_2/dataset_power_part2_2.csv" \
               "./Part2/Part2_2/dataset_power_alt_part2_2.csv" \
               "$PART2_2_OLD" "$PART2_2_NEW" \
    "Part2_3" "./Part2/Part2_3/dataset_power_part2_3.csv" \
               "./Part2/Part2_3/dataset_power_alt_part2_3.csv" \
               "$PART2_3_OLD" "$PART2_3_NEW"

# Part3
check_part "Part3" \
    "Part3_1" "./Part3/Part3_1/dataset_power_part3_1.csv" \
               "./Part3/Part3_1/dataset_power_alt_part3_1.csv" \
               "$PART3_1_OLD" "$PART3_1_NEW" \
    "Part3_2" "./Part3/Part3_2/dataset_power_part3_2.csv" \
               "./Part3/Part3_2/dataset_power_alt_part3_2.csv" \
               "$PART3_2_OLD" "$PART3_2_NEW" \
    "Part3_3" "./Part3/Part3_3/dataset_power_part3_3.csv" \
               "./Part3/Part3_3/dataset_power_alt_part3_3.csv" \
               "$PART3_3_OLD" "$PART3_3_NEW"

# Part4 (no sub-parts)
echo ""
echo "=========================================="
echo "Part4"
echo "=========================================="

PART4_OLD_FILE="./Part4/dataset_power_part4.csv"
PART4_NEW_FILE="./Part4/dataset_power_alt_part4.csv"

old_count=$(check_file "$PART4_OLD_FILE")
new_count=$(check_file "$PART4_NEW_FILE")

if [[ "$old_count" -eq "$PART4_OLD" ]]; then
    old_done="${GREEN}✓${NC}"
else
    old_done="${RED}✗${NC}"
fi

if [[ "$new_count" -eq "$PART4_NEW" ]]; then
    new_done="${GREEN}✓${NC}"
else
    new_done="${RED}✗${NC}"
fi

if [[ "$old_count" -eq "$PART4_OLD" ]] && [[ "$new_count" -eq "$PART4_NEW" ]]; then
    part4_status="${GREEN}DONE${NC}"
else
    part4_status="${YELLOW}PENDING${NC}"
fi

echo -e "  Part4 | ${old_done} Old: ${old_count}/${PART4_OLD} | ${new_done} New: ${new_count}/${PART4_NEW} | ${part4_status}"

if [[ "$old_count" -eq "$PART4_OLD" ]] && [[ "$new_count" -eq "$PART4_NEW" ]]; then
    echo -e "${GREEN}Part4 COMPLETE!${NC} (Old: $PART4_OLD rows, New: $PART4_NEW rows)"
else
    echo -e "${YELLOW}Part4 IN PROGRESS${NC} (Old: $PART4_OLD rows, New: $PART4_NEW rows total)"
fi

# GRAND TOTAL
echo ""
echo "==========================================================================="
echo "GRAND TOTAL"
echo "==========================================================================="

OLD_TOTAL=$((PART1_OLD_TOTAL+PART2_OLD_TOTAL+PART3_OLD_TOTAL+PART4_OLD))
NEW_TOTAL=$((PART1_NEW_TOTAL+PART2_NEW_TOTAL+PART3_NEW_TOTAL+PART4_NEW))
GRAND_TOTAL=$((OLD_TOTAL+NEW_TOTAL))

actual_old_total=0
actual_new_total=0

# Part1 subparts
for sub in Part1_1 Part1_2 Part1_3; do
    actual_old_total=$((actual_old_total+$(check_file "./Part1/$sub/dataset_power_$sub.csv" 2>/dev/null)))
    actual_new_total=$((actual_new_total+$(check_file "./Part1/$sub/dataset_power_alt_$sub.csv" 2>/dev/null)))
done

# Part2 subparts
for sub in Part2_1 Part2_2 Part2_3; do
    actual_old_total=$((actual_old_total+$(check_file "./Part2/$sub/dataset_power_$sub.csv" 2>/dev/null)))
    actual_new_total=$((actual_new_total+$(check_file "./Part2/$sub/dataset_power_alt_$sub.csv" 2>/dev/null)))
done

# Part3 subparts
for sub in Part3_1 Part3_2 Part3_3; do
    actual_old_total=$((actual_old_total+$(check_file "./Part3/$sub/dataset_power_$sub.csv" 2>/dev/null)))
    actual_new_total=$((actual_new_total+$(check_file "./Part3/$sub/dataset_power_alt_$sub.csv" 2>/dev/null)))
done

# Part4
actual_old_total=$((actual_old_total+$(check_file "./Part4/dataset_power_part4.csv" 2>/dev/null)))
actual_new_total=$((actual_new_total+$(check_file "./Part4/dataset_power_alt_part4.csv" 2>/dev/null)))

actual_total=$((actual_old_total+actual_new_total))

echo ""
echo "  Old Dataset:  $actual_old_total / $OLD_TOTAL rows"
echo "  New Dataset:  $actual_new_total / $NEW_TOTAL rows"
echo -e "  ${BLUE}Grand Total:  $actual_total / $GRAND_TOTAL rows${NC}"

if [[ "$actual_total" -eq "$GRAND_TOTAL" ]]; then
    echo -e "${GREEN}ALL DATASETS COMPLETE!${NC} (276,480 rows total)"
else
    remaining=$((GRAND_TOTAL-actual_total))
    echo -e "${YELLOW}Remaining: $remaining rows${NC}"
fi

echo ""
echo "==========================================================================="