PROJECT SPECIFICATION
1. Project Objective
Students are required to design, implement, and evaluate a software system capable of identifying or verifying individuals based on unique physiological or behavioral traits. The project must cover the entire pipeline from data acquisition to performance benchmarking.
2. Technical Requirements & Workflow
The implementation must follow these four mandatory phases:
Phase 1: Data Acquisition
•	Action: Students can select and utilize an established biometric image database (Public Datasets from sources like Kaggle, UCI, or Research Institutes), build one yourselves or use sensors (like cameras).
•	Requirement: Clearly document the source, scale (number of subjects/images), and specific characteristics of the chosen dataset.
Phase 2: Pre-processing (Optional but recommended)
•	Action: Apply image processing techniques to enhance the quality of the raw input.
•	Techniques: Noise reduction (Gaussian/Median filters), contrast enhancement (Histogram Equalization), image normalization, and Region of Interest (ROI) extraction (e.g., cropping the eye area for iris recognition).
Phase 3: Feature Extraction & Matching
Students can choose the methods for feature extracting and matching biometric features. Some popular approaches include:
•	Traditional approaches: Utilize hand-crafted feature descriptors (e.g., SIFT, SURF, LBP, HOG, or Gabor Filters) combined with classical Machine Learning classifiers (e.g., SVM, KNN, or Random Forest).
•	Deep Learning approaches: Implement or fine-tune Deep Learning architectures (e.g., CNNs, ResNet, MobileNet, or Vision Transformers) to perform automated end-to-end feature extraction and matching.
Phase 4: Performance Evaluation
A comprehensive analysis of the solution is required, including:
•	Accuracy Metrics: Calculation of FAR (False Acceptance Rate), FRR (False Rejection Rate), and EER (Equal Error Rate).
•	Computational Efficiency: Average execution time per sample (Latency).
•	Qualitative Analysis: A critical assessment of the solution’s strengths and weaknesses (e.g., sensitivity to lighting, pose variation, or hardware constraints).
3. Recommended Biometric Traits & Datasets
Students may select one of the following modalities for their project:
Biometric Trait	Recommended Public Datasets
Face	LFW (Labeled Faces in the Wild), CelebA, CASIA-WebFace.
Fingerprint	FVC2002, FVC2004, NIST Special Database.
Iris	CASIA-Iris, IIT Delhi Iris Database.
Palmprint	PolyU Palmprint, CASIA-Palmprint.
Gait (Shape/Movement)	CASIA Gait Database, OU-ISIR.
Vascular (Vein)	SDUMLA-HMT, PolyU Multispectral Palmprint.

4. Deliverables
1.	Technical Report: A detailed document describing the methodology, algorithms, and results.
2.	Source Code: Fully functional code (Python, C++, or MATLAB) with a README file.
3.	Presentation & Demo: A slide deck and a live/recorded demonstration of the authentication process.
5. Student Proposals & Custom Topics
Students are encouraged to propose their own unique research topics beyond the standard list. Potential areas for innovation include:
-	Multimodal Biometric Systems: Integrating two or more traits (e.g., combining Face and Fingerprint) for enhanced security.
-	Specific Domain Applications: Applying biometric authentication to a particular real-world scenario (e.g., smart home access, mobile banking, or exam attendance systems).
Note: Students wishing to pursue a self-proposed topic must consult with and receive approval from the lecturer before proceeding.
