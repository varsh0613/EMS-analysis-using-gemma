# executor.py
import os

class EDAExecutor:
    """
    Executes Gemma-generated Python plotting code.
    """

    def __init__(self, plot_dir=None):
        if plot_dir is None:
            self.plot_dir = os.path.join(os.path.expanduser("~"), "Desktop", "uni", "gemma", "eda_plots")
        else:
            self.plot_dir = plot_dir
        os.makedirs(self.plot_dir, exist_ok=True)

    def execute(self, df, code_str):
        """
        Execute code in controlled locals. Return list of plot filenames.
        """
        local_vars = {"df": df, "plot_dir": self.plot_dir, "plot_files": [], "os": os}
        plot_files = []

        try:
            exec(code_str, {}, local_vars)
        except Exception as e:
            raise RuntimeError(f"Error executing plot code: {e}")

        # Expect Gemma to store generated plot filenames in `plot_files` variable
        if "plot_files" in local_vars and local_vars["plot_files"]:
            plot_files = local_vars["plot_files"]
        else:
            # fallback: grab all PNGs in plot_dir
            plot_files = [os.path.join(self.plot_dir, f) for f in os.listdir(self.plot_dir) if f.lower().endswith(".png")]

        return plot_files
