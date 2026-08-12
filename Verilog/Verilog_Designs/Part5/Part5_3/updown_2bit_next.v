module updown_2bit_next (
    input  wire [1:0] q,      // current state
    input  wire       up,     // 1 = increment, 0 = decrement
    output wire [1:0] q_next
);
    wire dec_bit0, dec_bit1, inc_bit0, inc_bit1;

    assign inc_bit0 = ~q[0];
    assign inc_bit1 = q[1] ^ q[0];

    assign dec_bit0 = ~q[0];
    assign dec_bit1 = q[1] ^ ~q[0];

    assign q_next[0] = up ? inc_bit0 : dec_bit0;
    assign q_next[1] = up ? inc_bit1 : dec_bit1;
endmodule