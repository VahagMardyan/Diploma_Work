module debouncer (input clk, rst_n, noisy_in, output reg clean_out);
    reg [15:0] count; reg sync_0, sync_1;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin count <= 0; clean_out <= 0; sync_0 <= 0; sync_1 <= 0; end
        else begin
            sync_0 <= noisy_in; sync_1 <= sync_0;
            if(sync_1 == clean_out) count <= 0;
            else begin
                count <= count + 1;
                if(count == 16'hFFFF) begin clean_out <= sync_1; count <= 0; end
            end
        end
    end
endmodule
