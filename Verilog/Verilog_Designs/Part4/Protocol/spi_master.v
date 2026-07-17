// spi_master.v - SPI Master (Mode 0)
module spi_master #(
    parameter DATA_W = 8
)(
    input  wire              clk,
    input  wire              rst_n,
    input  wire              start,
    input  wire [DATA_W-1:0] tx_data,
    output reg  [DATA_W-1:0] rx_data,
    output wire              sclk,
    output wire              mosi,
    input  wire              miso,
    output wire              cs_n,
    output reg               done
);
    reg [3:0] bit_cnt;
    reg [DATA_W-1:0] shift_reg;
    reg busy;
    
    assign sclk  = busy ? clk : 1'b0;
    assign mosi  = shift_reg[DATA_W-1];
    assign cs_n  = ~busy;
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy      <= 1'b0;
            done      <= 1'b0;
            bit_cnt   <= 0;
            shift_reg <= 0;
            rx_data   <= 0;
        end else begin
            if (start && !busy) begin
                busy      <= 1'b1;
                done      <= 1'b0;
                shift_reg <= tx_data;
                bit_cnt   <= 0;
            end else if (busy) begin
                if (bit_cnt < DATA_W) begin
                    shift_reg <= {shift_reg[DATA_W-2:0], miso};
                    bit_cnt   <= bit_cnt + 1;
                end else begin
                    rx_data <= shift_reg;
                    busy    <= 1'b0;
                    done    <= 1'b1;
                end
            end
        end
    end
endmodule
