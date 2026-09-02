module moving_average_filter(
	input wire clk, reset,
	input wire [7:0] data_in,
	output reg [7:0] data_out
);
	reg [7:0] sample0, sample1, sample2, sample3;

	wire [9:0] sum;
	always @(posedge clk) begin
		if(reset) begin
			sample0 <= 8'b0;
			sample1 <= 8'b0;
			sample2 <= 8'b0;
			sample3 <= 8'b0;
			data_out <= 8'b0;
		end else begin
			sample0 <= data_in;
			sample1 <= sample0;
			sample2 <= sample1;
			sample3 <= sample2;
			
			data_out <= sum[9:2];
		end
	end

	assign sum = sample0 + sample1 + sample2 + sample3;
endmodule