module decoder_2to4_noen (
    input  wire [1:0] sel,
    output wire [3:0] y
);
    assign y[0] = ~sel[1] & ~sel[0];
    assign y[1] = ~sel[1] &  sel[0];
    assign y[2] =  sel[1] & ~sel[0];
    assign y[3] =  sel[1] &  sel[0];
endmodule
