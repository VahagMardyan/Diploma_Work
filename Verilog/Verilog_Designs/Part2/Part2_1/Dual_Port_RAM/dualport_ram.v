module dualport_ram(
                      data_in_a                       ,//input
                      wr_en_a                         ,//input
                      addr_a                          ,//input
                      data_in_b                       ,//input
                      wr_en_b                         ,//input
                      addr_b                          ,//input
                      clk                             ,//input
                      data_out_a                      ,//output
                      data_out_b                       //output
                      )                               ;

input             clk                                 ;//declare clock  
input             wr_en_a, wr_en_b                    ;//write/read enable as input
input    [  2:0]  addr_a, addr_b                      ;//declare address lines
input    [127:0]  data_in_a, data_in_b                ;//declare 128 bit input data
output   [127:0]  data_out_a, data_out_b              ;//declare 128 bit output data

reg      [127:0]  data_out_a, data_out_b              ;//declare 128 bit output data
reg      [127:0]  ram_vector [7:0]                    ;//declare a register that hold memory
reg      [  2:0]  read_addr_a, read_addr_b            ;//declare temp read address

//FIX: ram_vector was being driven from two separate always blocks (one per
//port), which is illegal in Verilog when both ports could write the same
//address simultaneously. Combined into a single always block so there is
//only one driver for ram_vector, with explicit priority: if both ports try
//to write the same address on the same cycle, port A wins. Each port still
//independently reads/writes according to its own wr_en signal otherwise.
always @ (posedge clk)
   begin
      //--- Port A ---
      if (wr_en_a)
         ram_vector[addr_a]   <= data_in_a            ;//write the data into ram vector when write/read enable is 1
      else
         data_out_a           <= ram_vector[addr_a]   ;//read the data from ram vector

      //--- Port B ---
      if (wr_en_b && !(wr_en_a && (addr_a == addr_b)))
         ram_vector[addr_b]   <= data_in_b            ;//write the data into ram vector when write/read enable is 1, unless port A already claimed this address this cycle
      else if (!wr_en_b)
         data_out_b           <= ram_vector[addr_b]   ;//read the data from ram vector
   end

endmodule                                              //end of dual port RAM
