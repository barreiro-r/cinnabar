# Sample Scientific Article

## 1. Introduction
This is a demonstration of **cinnabar**, a scientific markdown renderer. It supports advanced features like equation referencing and automated bibliographies.

## 2. Methodology
We analyze the relationship between $E$ and $m$ as defined in Equation \eqref{relativity}.

### 2.1 Physics Equations
Here is a fundamental equation:
$$E = mc^2 \tag{2.1.1}$$

You can also use the alternative reference syntax to link back to (Equation 2.1.1) using `\ref{eq:2.1.1}`.

## 3. Results
Our findings are summarized in Figure \ref{fig:1.1}.

![[sample_plot.png|fig:1.1|title:Example Distribution Plot|desc:This plot shows a placeholder representation of data distribution used for demonstrating cinnabar's figure rendering capabilities.|size:600]]

## 4. Discussion
==_Important Note:_ All figures must be stored in the `figures/` subdirectory.==

This tool also detects DOIs and can fetch metadata: https://doi.org/10.1038/s41586-020-2012-7.

## References
Citations will appear in the navbar and at the end of the document.
