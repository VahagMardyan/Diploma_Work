module dualport_ram(
                      data_in_a                       ,
                      wr_en_a                         ,
                      addr_a                          ,
                      data_in_b                       ,
                      wr_en_b                         ,
                      addr_b                          ,
                      clk                             ,
                      data_out_a                      ,
                      data_out_b                       
                      )                               ;

input             clk                                 ;  
input             wr_en_a, wr_en_b                    ;
input    [  2:0]  addr_a, addr_b                      ;
input    [127:0]  data_in_a, data_in_b                ;
output reg [127:0]  data_out_a, data_out_b            ; 

reg      [127:0]  ram_vector [7:0]                    ;

always @ (posedge clk)
   begin
      // Port A
      if (wr_en_a)
         ram_vector[addr_a] <= data_in_a;
      data_out_a <= ram_vector[addr_a]; // Read-during-write behavior

      // Port B
      if (wr_en_b)
         ram_vector[addr_b] <= data_in_b;
      data_out_b <= ram_vector[addr_b];
   end

endmodule
