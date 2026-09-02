module cla_4bit (
    input [3:0] a, b,
    input cin,
    output [3:0] sum,
    output cout
);
    wire [3:0] p, g;
    wire [4:0] c;

    assign p = a ^ b;
    assign g = a & b;

    assign c[0] = cin;
    assign c[1] = g[0] | (p[0] & c[0]);
    assign c[2] = g[1] | (p[1] & g[0]) | (p[1] & p[0] & c[0]);
    assign c[3] = g[2] | (p[2] & g[1]) | (p[2] & p[1] & g[0]) | (p[2] & p[1] & p[0] & c[0]);
    assign c[4] = g[3] | (p[3] & g[2]) | (p[3] & p[2] & g[1]) | (p[3] & p[2] & p[1] & g[0]) | (p[3] & p[2] & p[1] & p[0] & c[0]);

    assign sum = p ^ c[3:0];
    assign cout = c[4];
endmodule

module cla_16bit (
    input [15:0] A, B,
    input Cin,
    output [15:0] Sum,
    output Cout
);
    wire c4, c8, c12;

    cla_4bit cla1 (.a(A[3:0]),   .b(B[3:0]),   .cin(Cin), .sum(Sum[3:0]),   .cout(c4));
    cla_4bit cla2 (.a(A[7:4]),   .b(B[7:4]),   .cin(c4),  .sum(Sum[7:4]),   .cout(c8));
    cla_4bit cla3 (.a(A[11:8]),  .b(B[11:8]),  .cin(c8),  .sum(Sum[11:8]),  .cout(c12));
    cla_4bit cla4 (.a(A[15:12]), .b(B[15:12]), .cin(c12), .sum(Sum[15:12]), .cout(Cout));
endmodule