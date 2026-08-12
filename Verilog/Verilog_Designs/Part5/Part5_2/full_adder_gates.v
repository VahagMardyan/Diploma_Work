module full_adder_gates (
    input  wire a,
    input  wire b,
    input  wire cin,
    output wire sum,
    output wire cout
);
    wire ab_xor;
    assign ab_xor = a ^ b;
    assign sum    = ab_xor ^ cin;
    assign cout   = (a & b) | (cin & ab_xor);
endmodule