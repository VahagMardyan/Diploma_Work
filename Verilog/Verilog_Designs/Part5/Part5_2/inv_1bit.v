module inv_1bit (
    input  wire a,
    output wire y
);
    assign y = ~a;
endmodule