module sipo_reg #(parameter W=16) (input clk, rst_n, sin, output reg [W-1:0] pout);
    always @(posedge clk or negedge rst_n)
        if(!rst_n) pout <= 0; else pout <= {pout[W-2:0], sin};
endmodule
