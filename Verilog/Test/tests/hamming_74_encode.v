module hamming_74_encode (
    input  [3:0] data, // d[3], d[2], d[1], d[0]
    output [6:0] code  // p[1], p[2], d[0], p[3], d[1], d[2], d[3]
);
    wire p1, p2, p3;

    assign p1 = data[0] ^ data[1] ^ data[3];
    assign p2 = data[0] ^ data[2] ^ data[3];
    assign p3 = data[1] ^ data[2] ^ data[3];

    assign code = {data[3:1], p3, data[0], p2, p1};
endmodule