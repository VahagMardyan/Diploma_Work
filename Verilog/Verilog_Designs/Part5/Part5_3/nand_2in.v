module nand_2in (
    input  wire a,
    input  wire b,
    output wire y
);
    assign y = ~(a & b);
endmodule