module piso_reg #(parameter W=16) (input clk, rst_n, load, input [W-1:0] pin, output reg sout);
    reg [W-1:0] shift_reg;
    always @(posedge clk or negedge rst_n)
        if(!rst_n) begin shift_reg <= 0; sout <= 0; end
        else if(load) shift_reg <= pin;
        else begin sout <= shift_reg[W-1]; shift_reg <= {shift_reg[W-2:0], 1'b0}; end
endmodule 