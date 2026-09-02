module up_down_load_counter #(parameter W=8) (input clk, rst_n, load, up_dn, input [W-1:0] data_in, output reg [W-1:0] count);
    always @(posedge clk or negedge rst_n)
        if(!rst_n) count <= 0;
        else if(load) count <= data_in;
        else if(up_dn) count <= count + 1;
        else count <= count - 1;
endmodule