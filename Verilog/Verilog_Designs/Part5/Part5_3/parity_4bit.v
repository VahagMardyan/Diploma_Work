module parity_4bit (
    input  wire [3:0] d,
    output wire parity
);
    assign parity = d[0] ^ d[1] ^ d[2] ^ d[3];
endmodule
