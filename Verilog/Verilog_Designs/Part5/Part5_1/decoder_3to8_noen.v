module decoder_3to8_noen (
    input  wire [2:0] sel,
    output wire [7:0] y
);
    assign y[0] = ~sel[2] & ~sel[1] & ~sel[0];
    assign y[1] = ~sel[2] & ~sel[1] &  sel[0];
    assign y[2] = ~sel[2] &  sel[1] & ~sel[0];
    assign y[3] = ~sel[2] &  sel[1] &  sel[0];
    assign y[4] =  sel[2] & ~sel[1] & ~sel[0];
    assign y[5] =  sel[2] & ~sel[1] &  sel[0];
    assign y[6] =  sel[2] &  sel[1] & ~sel[0];
    assign y[7] =  sel[2] &  sel[1] &  sel[0];
endmodule
