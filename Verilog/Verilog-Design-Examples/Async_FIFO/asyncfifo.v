module asyncfifo(
                 write_clk                             ,
                 read_clk                              ,
                 reset                                 ,
                 write_en                              ,
                 read_en                               ,
                 data_in                               ,
                 mem_full                              ,
                 mem_empty                             ,
                 out                                    
                 )                                 ;

input            write_clk, read_clk, reset, write_en, read_en ;
input      [7:0] data_in                                       ;
output           mem_full, mem_empty                           ;
output reg [7:0] out                                           ;

reg        [7:0] mem [0:7]       ;
reg        [3:0] write_ptr, read_ptr ;

wire       [3:0] write_ptr_gray, read_ptr_gray;
reg        [3:0] wptr_sync_1, wptr_sync_2;
reg        [3:0] rptr_sync_1, rptr_sync_2;

// Binary to Gray conversion
assign write_ptr_gray = write_ptr ^ (write_ptr >> 1);
assign read_ptr_gray  = read_ptr  ^ (read_ptr  >> 1);

// Synchronize Read Pointer into Write Clock Domain
always @ (posedge write_clk or negedge reset) begin
   if(!reset) begin
      rptr_sync_1 <= 4'b0;
      rptr_sync_2 <= 4'b0;
   end else begin
      rptr_sync_1 <= read_ptr_gray;
      rptr_sync_2 <= rptr_sync_1;
   end
end

// Synchronize Write Pointer into Read Clock Domain
always @ (posedge read_clk or negedge reset) begin
   if(!reset) begin
      wptr_sync_1 <= 4'b0;
      wptr_sync_2 <= 4'b0;
   end else begin
      wptr_sync_1 <= write_ptr_gray;
      wptr_sync_2 <= wptr_sync_1;
   end
end

// Flags logic using Gray Code
assign mem_empty = (read_ptr_gray == wptr_sync_2);
assign mem_full  = (write_ptr_gray == {~rptr_sync_2[3:2], rptr_sync_2[1:0]});

/* Write Logic */
always @ (posedge write_clk or negedge reset) begin
   if(!reset) begin
      write_ptr <= 4'b0;
   end else if(write_en && !mem_full) begin
      mem[write_ptr[2:0]] <= data_in;
      write_ptr           <= write_ptr + 1'b1;
   end
end

/* Read Logic */
always @ (posedge read_clk or negedge reset) begin
   if(!reset) begin
      read_ptr <= 4'b0;
      out      <= 8'b0;
   end else if(read_en && !mem_empty) begin
      out      <= mem[read_ptr[2:0]];
      read_ptr <= read_ptr + 1'b1;
   end
end

endmodule
