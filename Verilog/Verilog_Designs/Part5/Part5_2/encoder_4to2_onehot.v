module encoder_4to2_onehot (
    input  wire [3:0] din,
    output wire [1:0] dout
);
    assign dout[0] = din[1] | din[3];
    assign dout[1] = din[2] | din[3];
endmodule