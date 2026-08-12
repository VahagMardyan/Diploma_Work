module mux2to1_gates (
    input  wire a,
    input  wire b,
    input  wire sel,
    output wire y
);
    wire nsel, t0, t1;
    assign nsel = ~sel;
    assign t0   = a & nsel;
    assign t1   = b & sel;
    assign y    = t0 | t1;
endmodule