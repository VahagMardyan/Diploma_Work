// uart_rx.v - UART Receiver (8-N-1)
module uart_rx (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       rx_in,
    output reg  [7:0] rx_data,
    output reg        rx_done
);
    localparam IDLE  = 2'b00,
               START = 2'b01,
               DATA  = 2'b10,
               STOP  = 2'b11;
    
    reg [1:0] state;
    reg [3:0] bit_cnt;
    reg [7:0] data_reg;
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state    <= IDLE;
            rx_data  <= 0;
            rx_done  <= 1'b0;
            bit_cnt  <= 0;
            data_reg <= 0;
        end else begin
            case (state)
                IDLE: begin
                    if (!rx_in) begin      // Start bit detected
                        state   <= START;
                        rx_done <= 1'b0;
                        bit_cnt <= 0;
                    end
                end
                START: begin
                    state <= DATA;
                end
                DATA: begin
                    data_reg[bit_cnt] <= rx_in;
                    bit_cnt <= bit_cnt + 1;
                    if (bit_cnt == 8) begin
                        state <= STOP;
                    end
                end
                STOP: begin
                    if (rx_in) begin
                        rx_data <= data_reg;
                        rx_done <= 1'b1;
                        state   <= IDLE;
                    end
                end
            endcase
        end
    end
endmodule
