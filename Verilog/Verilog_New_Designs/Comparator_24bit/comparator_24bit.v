module comparator_24bit #(parameter n = 24)(
    input wire [n-1:0] a,
    input wire [n-1:0] b,
    output wire lt,
    output wire eq,
    output wire gt
);
    assign eq = (a == b);
    assign lt = (a < b);
    assign gt = (a > b);    
endmodule
