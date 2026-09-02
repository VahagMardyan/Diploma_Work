module accumulator_16bit (input clk, rst_n, clear, input [15:0] din, output reg [15:0] acc);
    always @(posedge clk or negedge rst_n)
        if(!rst_n) acc <= 0;
        else if(clear) acc <= 0;
        else acc <= acc + din;
endmodule