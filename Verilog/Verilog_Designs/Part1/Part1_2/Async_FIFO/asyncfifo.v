module asyncfifo(
                 write_clk                             ,//input write clock
                 read_clk                              ,//input read clock 
                 reset                                 ,//input reset
                 write_en                              ,//input write enable
                 read_en                               ,//input read enable
                 data_in                               ,//input data
                 mem_full                              ,//output memory full 
                 mem_empty                             ,//output memory empty
                 out                                    //output data
                 )                                     ;

//port declarations
input            write_clk, read_clk, reset, write_en, read_en ;//input
input      [7:0] data_in                                       ;//input
output           mem_full, mem_empty                           ;//output
output reg [7:0] out                                           ;//output

reg        [7:0] mem [0:7]                            ;//8 * 8 memory
reg        [3:0] write_ptr                           ;//write pointer (addr + wrap bit)
reg        [3:0] read_ptr                            ;//read pointer (addr + wrap bit)

// Pointer MSB tracks FIFO wrap; avoids a shared count register with
// multiple drivers on separate clock domains.
assign mem_empty = (write_ptr == read_ptr)                    ;
assign mem_full  = (write_ptr[2:0] == read_ptr[2:0]) &&
                   (write_ptr[3]   != read_ptr[3])            ;

/* Write pointer and memory write */
always @ (posedge write_clk or negedge reset)
   begin
      if(!reset)
         begin
            write_ptr <= 4'b0                         ;//reset pointer
         end
      else
         begin
            if(write_en == 1 && !mem_full)
               begin
                  mem[write_ptr[2:0]] <= data_in           ;//data is written 
                  write_ptr           <= write_ptr + 1'b1  ;//pointer increment
               end
         end
    end

/* Read pointer and memory read */
always @ (posedge read_clk or negedge reset)
   begin
      if(!reset)
         begin
            read_ptr <= 4'b0                          ;//reset pointer
            out      <= 8'b0                          ;
         end
      else
         begin
            if(read_en == 1 && !mem_empty)
               begin
                  out      <= mem[read_ptr[2:0]]             ;//data is read 
                  read_ptr <= read_ptr + 1'b1                ;//pointer increment
               end
         end
    end

endmodule                                              //end of async FIFO
