module hamming_74_decode (
    input  [6:0] code,
    output [3:0] data,
    output error_detected
);
    wire p1, p2, p3;
    wire c1, c2, c3;
    wire [2:0] syndrome;

    assign p1 = code[0];
    assign p2 = code[1];
    assign data[0] = code[2];
    assign p3 = code[3];
    assign data[1] = code[4];
    assign data[2] = code[5];
    assign data[3] = code[6];

    assign c1 = p1 ^ data[0] ^ data[1] ^ data[3];
    assign c2 = p2 ^ data[0] ^ data[2] ^ data[3];
    assign c3 = p3 ^ data[1] ^ data[2] ^ data[3];
    
    assign syndrome = {c3, c2, c1};
    assign error_detected = (syndrome != 3'b000);

endmodule