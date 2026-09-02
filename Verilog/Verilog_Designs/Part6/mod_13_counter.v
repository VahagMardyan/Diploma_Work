module mod_13_counter (input clk, rst_n, enable, output reg [3:0] count);
    always @(posedge clk or negedge rst_n)
        if(!rst_n) count <= 0;
        else if(enable) count <= (count == 12) ? 0 : count + 1;
endmodule