module fir_param #(
    parameter TAPS    = 4,
    parameter DATA_W  = 8,
    parameter COEFF_W = 8,
    parameter ACC_W   = 16
)(
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire                     en,
    input  wire signed [DATA_W-1:0] x,
    output reg  signed [ACC_W-1:0]  y
);

    reg signed [DATA_W-1:0] dly [0:TAPS-1];
    reg signed [ACC_W-1:0]  sum_comb;
    
    wire signed [COEFF_W-1:0] C [0:3];
    assign C[0] = 8'h08;
    assign C[1] = 8'h10;
    assign C[2] = 8'h10;
    assign C[3] = 8'h08;

    integer i;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < TAPS; i = i + 1) begin
                dly[i] <= {DATA_W{1'b0}};
            end
            y <= {ACC_W{1'b0}};
        end else if (en) begin
            dly[0] <= x;
            for (i = 1; i < TAPS; i = i + 1) begin
                dly[i] <= dly[i-1];
            end
            y <= sum_comb;
        end
    end

    always @(*) begin
        sum_comb = {ACC_W{1'b0}};
        for (i = 0; i < TAPS; i = i + 1) begin
            sum_comb = sum_comb + (dly[i] * C[i]);
        end
    end

endmodule