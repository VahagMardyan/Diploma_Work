// fir_param.v - FIR filter (transposed form)
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
    // Coefficients (signed, 2's complement)
    // Example: 4-tap low-pass {8, 16, 16, 8}
    localparam [COEFF_W-1:0] C [0:TAPS-1] = {
        8'h08, 8'h10, 8'h10, 8'h08
    };
    
    reg signed [DATA_W-1:0]  dly [0:TAPS-1];
    reg signed [ACC_W-1:0]   mul [0:TAPS-1];
    integer i;
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i=0; i<TAPS; i=i+1) begin
                dly[i] <= 0;
                mul[i] <= 0;
            end
            y <= 0;
        end else if (en) begin
            // Shift register
            for (i=TAPS-1; i>0; i=i-1) begin
                dly[i] <= dly[i-1];
            end
            dly[0] <= x;
            
            // Multiply and sum
            y <= 0;
            for (i=0; i<TAPS; i=i+1) begin
                y <= y + dly[i] * C[i];
            end
        end
    end
endmodule
