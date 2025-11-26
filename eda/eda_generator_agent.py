# generator.py
import textwrap
import os
import re

class EDAGenerator:
    """
    Interface to Gemma: send dataset, get summaries, plot code, interpretations.
    """

    def __init__(self, llm_client):
        self.llm = llm_client

    def get_summary(self, df):
        """
        Ask Gemma for dataset summary (plain text).
        """
        prompt = textwrap.dedent(f"""
        You are an expert EMS analyst. Summarize this dataset for EDA purposes.
        Include:
        - key statistics
        - missing values
        - top numeric & categorical insights
        - operationally/clinically relevant info
        DATA SAMPLE:
        {df.head(50).to_dict(orient='records')}
        """)
        return self._call_gemma(prompt)

    def get_plot_code(self, df, summary_text):
        """
        Ask Gemma to generate Python code to produce plots for the dataset.
        """
        prompt = textwrap.dedent(f"""
        You are an expert data analyst.

        You are generating *executable Python code* for plotting.
        VERY IMPORTANT RULES:
        1. Use ONLY the columns that actually exist in the dataframe.
        Here is the full list of valid columns:
        {list(df.columns)}

        2. You MUST NOT invent or assume columns.
        3. You MUST NOT load any CSV files or external data.
        4. You MUST use the df variable that is already provided.
        5. The variable `plot_dir` (absolute path string) and `plot_files` (list) are already defined for you.
        6. You MUST save every plot using `os.path.join(plot_dir, "filename.png")`.
        7. You MUST append the full path of each saved plot to `plot_files`.
        8. You MUST import matplotlib.pyplot as plt, seaborn as sns, and os.

        CRITICAL ROBUSTNESS RULES:
        9. Wrap EACH individual plot generation in a try-except block. 
           If a plot fails, print the error and continue to the next one.
           Example:
           try:
               # ... code to generate plot ...
               # ... code to save plot ...
           except Exception as e:
               print(f"Plot failed: {e}")

        10. When aggregating (e.g. value_counts), use strict column naming.
            Do NOT use spaces in column names.
            Example:
            counts = df['Category'].value_counts().reset_index()
            counts.columns = ['category_val', 'count_val']  # Explicitly rename
            sns.barplot(data=counts, x='category_val', y='count_val')

        11. If calculating time differences (durations), YOU MUST convert columns to datetime first.
            df['Time1'] = pd.to_datetime(df['Time1'], errors='coerce')
            df['Time2'] = pd.to_datetime(df['Time2'], errors='coerce')
            # Check for valid data before plotting
            
        12. Avoid using 'palette' in seaborn unless you also set `hue` to the same variable.
            Prefer `color='skyblue'` or similar single colors for simple bar plots.

        Using the dataset summary below:
        {summary_text}

        Generate Python plotting code using seaborn and matplotlib.
        Return ONLY runnable Python code — no markdown, no explanations.
        """)

        return self._call_gemma(prompt)

    def get_interpretations(self, plot_paths, summary_text):
        """
        Ask Gemma to interpret each plot. `plot_paths` is list of absolute filenames.
        Returns a dictionary mapping absolute path -> interpretation text.
        """
        # Create a mapping of basename -> full path to help mapping back
        path_map = {os.path.basename(p): p for p in plot_paths}
        plot_filenames = list(path_map.keys())

        prompt = textwrap.dedent(f"""
        You are an expert EMS analyst. Based on the dataset summary:
        {summary_text}

        Interpret the following plots:
        {plot_filenames}

        Provide 4-6 line explanation per plot. 
        You MUST Return the response in this strict format for every plot:
        PLOT_FILENAME: <filename>
        INTERPRETATION: <interpretation text>
        END_INTERPRETATION
        """)
        
        response = self._call_gemma(prompt)
        
        # Parse the response
        interpretations = {}
        current_file = None
        current_text = []
        
        for line in response.splitlines():
            line = line.strip()
            if line.startswith("PLOT_FILENAME:"):
                current_file = line.replace("PLOT_FILENAME:", "").strip()
                current_text = []
            elif line == "END_INTERPRETATION":
                if current_file:
                    # Map back to full path if possible
                    full_path = path_map.get(current_file, current_file)
                    # If exact match failed, try fuzzy match (some LLMs strip extensions or add quotes)
                    if full_path not in path_map.values():
                        for base, full in path_map.items():
                            if base in current_file or current_file in base:
                                full_path = full
                                break
                    
                    interpretations[full_path] = "\n".join(current_text).strip()
                    current_file = None
            elif current_file:
                current_text.append(line)
                
        return interpretations

    def get_insights_and_recommendations(self, summary_text, interpretations):
        """
        Generate final insights and recommendations based on summary and plot interpretations.
        """
        # Combine all interpretations into one text block
        all_interps = "\n".join([f"Plot: {os.path.basename(k)}\nAnalysis: {v}" for k, v in interpretations.items()])
        
        prompt = textwrap.dedent(f"""
        You are an expert senior data analyst.
        Based on the dataset summary:
        {summary_text}

        And the analysis of the plots:
        {all_interps}

        Provide:
        1. 5 Key Strategic Insights (bullet points)
        2. 5 Actionable Recommendations (bullet points)

        Format your response exactly as:
        INSIGHTS:
        - Insight 1
        - Insight 2
        ...
        RECOMMENDATIONS:
        - Rec 1
        - Rec 2
        ...
        """)

        response = self._call_gemma(prompt)
        
        insights = []
        recommendations = []
        mode = None
        
        for line in response.splitlines():
            line = line.strip()
            if line == "INSIGHTS:":
                mode = "insights"
            elif line == "RECOMMENDATIONS:":
                mode = "recommendations"
            elif line.startswith("-"):
                content = line.lstrip("- ").strip()
                if mode == "insights":
                    insights.append(content)
                elif mode == "recommendations":
                    recommendations.append(content)
                    
        return insights, recommendations

    def _call_gemma(self, prompt):
        try:
            if hasattr(self.llm, "chat"):
                system = {"role": "system", "content": "You are a precise EDA assistant."}
                user = {"role": "user", "content": prompt}
                return self.llm.chat([system, user])
            elif hasattr(self.llm, "generate_text"):
                return self.llm.generate_text(prompt)
            else:
                return self.llm.ask(prompt)
        except Exception as e:
            return f"LLM_CALL_ERROR: {e}"
