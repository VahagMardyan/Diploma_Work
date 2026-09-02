module lfsr_16bit (input clk, rst_n, output reg [15:0] q);
    always @(posedge clk or negedge rst_n)
        if(!rst_n) q <= 16'hACE1;
        else q <= {q[14:0], q[15] ^ q[13] ^ q[12] ^ q[10]};
endmodule
