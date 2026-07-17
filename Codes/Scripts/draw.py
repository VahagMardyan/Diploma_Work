"""
This code visualizes Neural Network.
"""
import torch
from torchview import draw_graph
from torchinfo import summary

from model import PowerNet

def visualize():
    model = PowerNet(input_dim=34)
    model.eval()
    dummy_input = torch.randn(1, 34)

    print("="*10 + " 1. TEXT SUMMARY (TORCHINFO) " + "="*10)

    summary(model, input_size=(1, 34))

    print("\n" + "="*10 + " 2. EXPORTING TO ONNX FOR NETRON " + "="*10)

    onnx_path = "model_architecture.onnx"

    torch.onnx.export(
        model, 
        dummy_input, 
        onnx_path, 
        input_names=['input_features'], 
        output_names=['predicted_power'],
        dynamic_axes={'input_features': {0: 'batch_size'}, 'predicted_power': {0: 'batch_size'}}
    )

    print(f"Successfully saved ONNX model to: {onnx_path}")
    print("You can upload this file directly to https://netron.app/ to view it!")

    print("\n" + "="*10 + " 3. GENERATING PNG DIAGRAM (TORCHVIEW) " + "="*10)

    try:
        model_graph = draw_graph(
            model, 
            input_data=dummy_input,
            graph_name="Power_Predictor_Graph",
            expand_nested=True,
            depth=2
        )
        model_graph.visual_graph.render(format="png")
        print("Successfully generated 'Power_Predictor_Graph.png'!")
    except Exception as e:
        print(f"Graphviz rendering skipped or failed: {e}")
        print("Don't worry, you can still use the ONNX file with Netron to get screenshots!")

if __name__ == "__main__":
    visualize()

