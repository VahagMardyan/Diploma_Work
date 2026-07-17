module adder_12bit(
    input wire [11:0] a,
    input wire [11:0] b,
    input wire cin,
    output wire [11:0] sum,
    output wire cout
);
    assign {cout, sum} = {1'b0, a} + {1'b0, b} + {12'b0 ,cin};
endmodule
