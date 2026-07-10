module syncfifo(
    input            clk,
    input            reset, // Synchronous active-high reset
    input            write_en,
    input            read_en,
    input      [7:0] data_in,
    output           full,
    output           empty,
    output reg [7:0] out
);

reg [7:0] memory_vec   [0:7];
reg [2:0] write_pointer;
reg [2:0] read_pointer;
reg [3:0] count;

assign full  = (count == 4'd8);
assign empty = (count == 4'd0);

// Write Pointer and Memory Logic
always @ (posedge clk) begin
    if (reset) begin
        write_pointer <= 3'b0;
    end else begin
        if (write_en && !full) begin
            memory_vec[write_pointer] <= data_in;
            write_pointer             <= write_pointer + 1'b1;
        end
    end
end

// Read Pointer and Output Logic
always @ (posedge clk) begin
    if (reset) begin
        read_pointer <= 3'b0;
        out          <= 8'b0;
    end else begin
        if (read_en && !empty) begin
            out          <= memory_vec[read_pointer];
            read_pointer <= read_pointer + 1'b1;
        end
    end
end

// Counter Logic
always @(posedge clk) begin
    if (reset) begin
        count <= 4'b0;
    end else begin
        case({write_en, read_en})
            2'b10  : if (!full)  count <= count + 1'b1;
            2'b01  : if (!empty) count <= count - 1'b1;
            2'b11  : count <= count; // Միաժամանակյա կարդալ և գրել
            default: count <= count;
        endcase 
    end
end

endmodule
