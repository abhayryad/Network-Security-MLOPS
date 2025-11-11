import os
import sys

from networksecurity.exception.exception import NetworkSecurityException 
from networksecurity.logging.logger import logging
from networksecurity.entity.artifact_entity import DataTransformationArtifact,ModelTrainerArtifact
from networksecurity.entity.config_entity import ModelTrainerConfig
from networksecurity.utils.ml_utils.model.estimator import NetworkModel
from networksecurity.utils.main_utils.utils import save_object,load_object
from networksecurity.utils.main_utils.utils import load_numpy_array_data,evaluate_models
from networksecurity.utils.ml_utils.metric.classification_metric import get_classification_score
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import r2_score
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import (
    AdaBoostClassifier,
    GradientBoostingClassifier,
    RandomForestClassifier,
)
import mlflow
from urllib.parse import urlparse

# NOTE: The credentials below should ideally be loaded from a configuration or environment file.
os.environ["MLFLOW_TRACKING_URI"]="https://dagshub.com/abhayryad/Network-Security-MLOPS.mlflow"
os.environ["MLFLOW_TRACKING_USERNAME"]="abhayryad"
os.environ["MLFLOW_TRACKING_PASSWORD"]="b31f2584637a105ae39dac8d1780fc97857f834a"

# --- Start of ModelTrainer Class ---

class ModelTrainer:
    def __init__(self,model_trainer_config:ModelTrainerConfig,data_transformation_artifact:DataTransformationArtifact):
        try:
            self.model_trainer_config=model_trainer_config
            self.data_transformation_artifact=data_transformation_artifact
        except Exception as e:
            # FIX: Removed ',sys' to fix TypeError
            raise NetworkSecurityException(e)
        
    def track_mlflow(self,best_model, classification_train_metric, classification_test_metric):
        # NOTE: Remove set_registry_uri unless needed for specific MLflow registry features
        # mlflow.set_registry_uri("https://dagshub.com/abhayryad/Network-Security-MLOPS.mlflow")

        with mlflow.start_run():
            # Log Training Metrics
            mlflow.log_metric("train_f1_score", classification_train_metric.f1_score)
            mlflow.log_metric("train_precision", classification_train_metric.precision_score)
            mlflow.log_metric("train_recall_score", classification_train_metric.recall_score)
            
            # Log Testing Metrics
            mlflow.log_metric("test_f1_score", classification_test_metric.f1_score)
            mlflow.log_metric("test_precision", classification_test_metric.precision_score)
            mlflow.log_metric("test_recall_score", classification_test_metric.recall_score)

            # FIX: The path handling for MLflow artifact logging was incorrect (it created 
            # a directory named "model" inside the trained_model_file_path).
            # We must create a dedicated directory for MLflow artifacts and save the model file there.
            
            # 1. Define a temporary, clean path for the MLflow artifact save
            mlflow_artifact_dir = os.path.join(os.path.dirname(self.model_trainer_config.trained_model_file_path), "mlflow_artifacts_temp")
            temp_model_file_path = os.path.join(mlflow_artifact_dir, "best_model.pkl")

            # 2. Ensure directory exists
            os.makedirs(mlflow_artifact_dir, exist_ok=True)
            
            # 3. Save the best_model using your utility
            save_object(temp_model_file_path, obj=best_model)
            
            # 4. Log the saved model file as an artifact
            mlflow.log_artifact(temp_model_file_path, artifact_path="model")

            logging.info("MLflow model and metrics successfully tracked.")

    def train_model(self,X_train,y_train,x_test,y_test):
        models = {
            "Random Forest": RandomForestClassifier(verbose=1),
            "Decision Tree": DecisionTreeClassifier(),
            "Gradient Boosting": GradientBoostingClassifier(verbose=1),
            "Logistic Regression": LogisticRegression(verbose=1),
            "AdaBoost": AdaBoostClassifier(),
        }
        params={
            "Decision Tree": {
                'criterion':['gini', 'entropy', 'log_loss'],
            },
            "Random Forest":{
                'n_estimators': [8,16,32,128,256]
            },
            "Gradient Boosting":{
                'learning_rate':[.1,.01,.05,.001],
                'subsample':[0.6,0.7,0.75,0.85,0.9],
                'n_estimators': [8,16,32,64,128,256]
            },
            "Logistic Regression":{},
            "AdaBoost":{
                'learning_rate':[.1,.01,.001],
                'n_estimators': [8,16,32,64,128,256]
            }
        }
        model_report:dict=evaluate_models(X_train=X_train,y_train=y_train,X_test=x_test,y_test=y_test,
                                         models=models,param=params)
        
        ## To get best model score from dict
        best_model_score = max(sorted(model_report.values()))

        ## To get best model name from dict
        best_model_name = list(model_report.keys())[
            list(model_report.values()).index(best_model_score)
        ]
        best_model = models[best_model_name]
        
        # Calculate Metrics
        y_train_pred=best_model.predict(X_train)
        classification_train_metric=get_classification_score(y_true=y_train,y_pred=y_train_pred)
        
        y_test_pred=best_model.predict(x_test)
        classification_test_metric=get_classification_score(y_true=y_test,y_pred=y_test_pred)

        ## Track the experiements with mlflow (Called once with both metrics)
        self.track_mlflow(best_model, classification_train_metric, classification_test_metric)

        # Save model locally (for deployment/next stage)
        preprocessor = load_object(file_path=self.data_transformation_artifact.transformed_object_file_path)
        
        model_dir_path = os.path.dirname(self.model_trainer_config.trained_model_file_path)
        os.makedirs(model_dir_path,exist_ok=True)

        Network_Model=NetworkModel(preprocessor=preprocessor,model=best_model)
        
        # This saves the final NetworkModel object (the pipeline)
        save_object(self.model_trainer_config.trained_model_file_path,obj=Network_Model)
        
        # Redundant and possibly conflicting save_object("final_model/model.pkl",best_model)
        save_object("final_model/model.pkl",best_model)
        
        ## Model Trainer Artifact
        model_trainer_artifact=ModelTrainerArtifact(trained_model_file_path=self.model_trainer_config.trained_model_file_path,
                                 train_metric_artifact=classification_train_metric,
                                 test_metric_artifact=classification_test_metric
                                 )
        logging.info(f"Model trainer artifact: {model_trainer_artifact}")
        return model_trainer_artifact
    
    def initiate_model_trainer(self)->ModelTrainerArtifact:
        try:
            train_file_path = self.data_transformation_artifact.transformed_train_file_path
            test_file_path = self.data_transformation_artifact.transformed_test_file_path

            #loading training array and testing array
            train_arr = load_numpy_array_data(train_file_path)
            test_arr = load_numpy_array_data(test_file_path)

            x_train, y_train, x_test, y_test = (
                train_arr[:, :-1],
                train_arr[:, -1],
                test_arr[:, :-1],
                test_arr[:, -1],
            )

            model_trainer_artifact=self.train_model(x_train,y_train,x_test,y_test)
            return model_trainer_artifact
            
        except Exception as e:
            # FIX: Removed ', sys' to fix TypeError
            raise NetworkSecurityException(e)