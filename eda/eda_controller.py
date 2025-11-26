# controller.py
import pandas as pd
from eda_generator_agent import EDAGenerator
from eda_executor import EDAExecutor
from eda_doc_builder import DocBuilder

class EDAController:
    """
    Orchestrates Gemma-driven EDA: summary → plots → interpretations → report → evaluation → rerun.
    """

    def __init__(self, llm_client, max_attempts=3):
        self.generator = EDAGenerator(llm_client)
        self.executor = EDAExecutor()
        self.builder = DocBuilder()
        self.max_attempts = max_attempts

    def run(self, df):
        for attempt in range(1, self.max_attempts+1):
            print(f"[EDAController] Attempt {attempt}...")
            try:
                # Step 1: Get dataset summary
                summary_text = self.generator.get_summary(df)

                # Step 2: Get plot code from Gemma
                plot_code = self.generator.get_plot_code(df, summary_text)

                # Step 3: Execute plots
                plot_paths = self.executor.execute(df, plot_code)

                # Step 4: Get interpretations for each plot
                interpretations = self.generator.get_interpretations(plot_paths, summary_text)

                # Step 5: Get Final Insights and Recommendations
                insights, recommendations = self.generator.get_insights_and_recommendations(summary_text, interpretations)

                # Step 6: Build report
                report_path = self.builder.build_report(
                    summary_text=summary_text,
                    df=df,
                    plot_paths=plot_paths,
                    interpretations=interpretations,
                    final_insights=insights,
                    recommendations=recommendations
                )

                # Step 7: Evaluate report (e.g., must have plots + interpretations)
                if len(plot_paths) == 0 or not interpretations:
                    raise RuntimeError("Report evaluation failed: missing plots or interpretations.")

                print(f"[EDAController] ✅ Report generated successfully: {report_path}")
                return report_path

            except Exception as e:
                print(f"[EDAController] Error during attempt {attempt}: {e}")
                continue

        raise RuntimeError("[EDAController] Failed after maximum attempts.")

# === RUN ===
if __name__ == "__main__":
    import os
    from llm_client import LLMClient  # implement to connect to your local Gemma

    csv_path = "C:\\Users\\SAHARA\\Downloads\\cleaned_ems_output2.csv"
    if not os.path.exists(csv_path):
        print("CSV file not found:", csv_path)
    else:
        df = pd.read_csv(csv_path)
        llm = LLMClient()
        controller = EDAController(llm_client=llm)
        controller.run(df)
