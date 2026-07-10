module no_1s (
              i_a, clk, reset, no_ones
              );

input clk, reset;
input       [15:0] i_a;
output reg  [3:0] no_ones;

integer k;
reg [3:0] temp_ones;

always @ (*) begin
   temp_ones = 4'd0;
   for (k = 0; k < 16; k = k + 1) begin
      temp_ones = temp_ones + {3'b000, i_a[k]};
   end
end

always @ (posedge clk) begin
   if (reset)
      no_ones <= 4'b0;
   else
      no_ones <= temp_ones;
end

endmodule
