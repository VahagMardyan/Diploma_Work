module demux1to2 (
    input  wire din,
    input  wire sel,
    output wire y0,
    output wire y1
);
    assign y0 = din & ~sel;
    assign y1 = din & sel;
endmodule