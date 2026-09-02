module sync_fifo_tiny (input clk, rst_n, wr_en, rd_en, input [7:0] din, output reg [7:0] dout, output full, empty);
    reg [7:0] mem [0:3]; reg [2:0] count; reg [1:0] wr_ptr, rd_ptr;
    assign empty = (count == 0); assign full = (count == 4);
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin count <= 0; wr_ptr <= 0; rd_ptr <= 0; dout <= 0; end
        else begin
            if(wr_en && !full) begin mem[wr_ptr] <= din; wr_ptr <= wr_ptr + 1; end
            if(rd_en && !empty) begin dout <= mem[rd_ptr]; rd_ptr <= rd_ptr + 1; end
            if(wr_en && !full && (!rd_en || empty)) count <= count + 1;
            else if(rd_en && !empty && (!wr_en || full)) count <= count - 1;
        end
    end
endmodule