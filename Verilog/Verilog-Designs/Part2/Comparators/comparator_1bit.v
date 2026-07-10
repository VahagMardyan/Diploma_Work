module comparator_1bit(input wire a, input wire b, output wire a_gt_b, output wire a_lt_b, output wire a_eq_b);
        assign a_gt_b = a & (~b);
        assign a_lt_b = (~a) & b;
        assign a_eq_b = ~(a^b);
endmodule