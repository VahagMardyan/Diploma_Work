module pipo_shift(
    input  [15:0] data_in,  
    input         load,    
    input  [1:0]  shift_en,
    input         clk,     
    input         reset,   
    output reg [15:0] data_out
);

always @ (posedge clk) begin
    if (reset) begin
        data_out <= 16'b0;
    end else if (load) begin
        case(shift_en)
            2'b00 : data_out <= data_in <<  1; // Shift left
            2'b01 : data_out <= data_in >>  1; // Shift right
            2'b10 : data_out <= $signed(data_in) <<< 1; // Arithmetic left
            2'b11 : data_out <= $signed(data_in) >>> 1; // Arithmetic right
        endcase
    end
end

endmodule