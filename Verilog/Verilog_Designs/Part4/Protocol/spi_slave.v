// spi_slave.v - SPI Slave (Mode 0)
module spi_slave #(
    parameter DATA_W = 8
)(
    input  wire              clk,
    input  wire              rst_n,
    input  wire              sclk,
    input  wire              mosi,
    output wire              miso,
    input  wire              cs_n,
    input  wire [DATA_W-1:0] tx_data,
    output reg  [DATA_W-1:0] rx_data,
    output reg               data_ready
);
    reg [DATA_W-1:0] shift_reg;
    reg [3:0] bit_cnt;
    reg sclk_prev;
    
    assign miso = shift_reg[DATA_W-1];
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            shift_reg  <= 0;
            bit_cnt    <= 0;
            rx_data    <= 0;
            data_ready <= 1'b0;
            sclk_prev  <= 1'b0;
        end else begin
            sclk_prev <= sclk;
            
            if (!cs_n) begin
                // Rising edge: sample MOSI
                if (sclk && !sclk_prev) begin
                    if (bit_cnt < DATA_W) begin
                        shift_reg <= {shift_reg[DATA_W-2:0], mosi};
                        bit_cnt   <= bit_cnt + 1;
                    end
                end
                // Falling edge: update MISO
                if (!sclk && sclk_prev) begin
                    if (bit_cnt == DATA_W) begin
                        rx_data    <= shift_reg;
                        data_ready <= 1'b1;
                        bit_cnt    <= 0;
                    end
                end
            end else begin
                bit_cnt    <= 0;
                data_ready <= 1'b0;
            end
        end
    end
endmodule
