// barrel_shifter.v - Parameterized barrel shifter (DC-compatible)
// Uses generate + for-loop for fully synthesizable hardware
module barrel_shifter #(
    parameter WIDTH     = 8,
    parameter ROTATE_EN = 0      // 0=shift (logical), 1=rotate
)(
    input  wire [WIDTH-1:0]           data,
    input  wire [$clog2(WIDTH)-1:0]   amt,
    input  wire                       dir,   // 0=right, 1=left
    output wire  [WIDTH-1:0]          out
);

    // LEFT SHIFT (logical, zero-fill)
    function [WIDTH-1:0] shift_left;
        input [WIDTH-1:0] d;
        input [$clog2(WIDTH)-1:0] s;
        integer i;
        begin
            shift_left = 0;
            for (i = 0; i < WIDTH; i = i + 1) begin
                if (i + s < WIDTH) begin
                    shift_left[i+s] = d[i];
                end else begin
                    shift_left[i+s - WIDTH] = 0;  // zero-fill (unused for shifts beyond width)
                end
            end
        end
    endfunction

    // RIGHT SHIFT (logical, zero-fill)
    function [WIDTH-1:0] shift_right;
        input [WIDTH-1:0] d;
        input [$clog2(WIDTH)-1:0] s;
        integer i;
        begin
            shift_right = 0;
            for (i = 0; i < WIDTH; i = i + 1) begin
                if (i + s < WIDTH) begin
                    shift_right[i] = d[i+s];
                end else begin
                    shift_right[i] = 0;
                end
            end
        end
    endfunction

    // LEFT ROTATE (circular)
    function [WIDTH-1:0] rotate_left;
        input [WIDTH-1:0] d;
        input [$clog2(WIDTH)-1:0] s;
        integer i;
        begin
            rotate_left = 0;
            for (i = 0; i < WIDTH; i = i + 1) begin
                rotate_left[(i + s) % WIDTH] = d[i];
            end
        end
    endfunction

    // RIGHT ROTATE (circular)
    function [WIDTH-1:0] rotate_right;
        input [WIDTH-1:0] d;
        input [$clog2(WIDTH)-1:0] s;
        integer i;
        begin
            rotate_right = 0;
            for (i = 0; i < WIDTH; i = i + 1) begin
                rotate_right[(i + WIDTH - s) % WIDTH] = d[i];
            end
        end
    endfunction

    // Main MUX
    wire [WIDTH-1:0] shifted_left, shifted_right, rotated_left, rotated_right;
    
    assign shifted_left  = shift_left(data, amt);
    assign shifted_right = shift_right(data, amt);
    assign rotated_left  = rotate_left(data, amt);
    assign rotated_right = rotate_right(data, amt);
    
    // Select output based on dir and ROTATE_EN
    generate
        if (ROTATE_EN == 1) begin : gen_rotate
            assign out = dir ? rotated_left : rotated_right;
        end else begin : gen_shift
            assign out = dir ? shifted_left : shifted_right;
        end
    endgenerate

endmodule
