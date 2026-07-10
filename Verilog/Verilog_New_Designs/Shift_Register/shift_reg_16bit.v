module shift_reg_16bit(
    input wire clk,
    input wire rst_n,
    input wire serial_in,
    output reg [15:0] parallel_out
);
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            parallel_out <= 16'b0;
        end else begin
            parallel_out <= {parallel_out[14:0], serial_in};
        end
    end
endmodule
