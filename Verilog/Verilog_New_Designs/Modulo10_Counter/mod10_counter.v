module mod10_counter(
    input wire clk,
    input wire rst_n,
    output reg [3:0] count
);
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
          count <= 4'b0000;
        end else if(count == 4'd9) begin
            count <= 4'b0000; // reset at 9
        end else begin
            count <= count + 1'b1;
        end
    end
endmodule
