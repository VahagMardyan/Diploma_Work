module gray_counter_5bit(
    input wire clk,
    input wire rst_n,
    output reg [4:0] gray_out
);
    reg [4:0] bin_count;

    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            bin_count <= 5'b00000;
            gray_out  <= 5'b00000;
        end else begin
            bin_count <= bin_count + 1'b1;
            gray_out  <= (bin_count + 1'b1) ^ ((bin_count + 1'b1) >> 1);
        end
    end
endmodule
