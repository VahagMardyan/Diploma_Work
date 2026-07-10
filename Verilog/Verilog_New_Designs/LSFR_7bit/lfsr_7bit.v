module lfsr_7bit(
    input wire clk,
    input wire rst_n,
    output reg [6:0] out
);
    wire feedback;
    assign feedback = out[6] ^ out[5]; // XOR Feedback
    
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
          out <= 7'b0000001;
        end
        else begin
          out <= {out[5:0], feedback};
        end
    end
endmodule
