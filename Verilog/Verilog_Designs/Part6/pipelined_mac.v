module pipelined_mac (input clk, rst_n, input [7:0] a, b, output reg [15:0] out);
    reg [15:0] mult_reg;
    always @(posedge clk or negedge rst_n)
        if(!rst_n) begin mult_reg <= 0; out <= 0; end
        else begin mult_reg <= a * b; out <= out + mult_reg; end
endmodule