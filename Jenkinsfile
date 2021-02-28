def getEnvFromBranch(branch) {
  if (branch == 'master') {
    return 'dev'
  } else {
    return branch
 }
}

pipeline {
    agent any
    environment {
        STAGE = getEnvFromBranch(env.BRANCH_NAME)
        scannerHome = "/home/drake/sonar"

    }
    stages {
        stage("Run tests") {
            steps {
                withPythonEnv('python3') {
                    sh 'pip3 install pytest coverage moto'
                    sh 'coverage run --source . -m pytest'
                    sh 'coverage xml'
                }
            }
        }    
        stage ('Sonarqube') {
            steps {
                withSonarQubeEnv('Sonarqube') {
                    sh "${scannerHome}/bin/sonar-scanner"
                }
            }
        }

        stage("Quality Gate") {
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    // Parameter indicates whether to set pipeline to UNSTABLE if Quality Gate fails
                    // true = set pipeline to UNSTABLE, false = don't
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        stage("Deploy") {
          when {
            anyOf {
              expression{(STAGE == 'dev')}
              expression{(STAGE == 'test')}
            }
            not { buildingTag() }
          }
          steps {
            echo 'Deploying to dev or test'
            sh 'serverless deploy --stage '+ STAGE + ' --aws-profile ' + STAGE
          }
        }
        stage("Deploy to Staging") {
          when {
            anyOf {
              expression{(env.BRANCH_NAME =~ 'release-\\d{1,2}\\.\\d{1,3}\\.\\d{1,3}-rc\\d{1,3}')}
            }
            beforeInput true
            buildingTag()
          }
          input {
              message "Should we deploy to staging?"
              ok "Engage"
          }
          steps{
            sh 'serverless deploy --stage stage  --aws-profile stage'
          }
        }
        stage("Deploy to Production") {
            when {
              expression{(env.BRANCH_NAME =~ 'release-\\d{1,2}\\.\\d{1,3}\\.\\d{1,3}$')}
              beforeInput true
              buildingTag()
            }
            input {
              message "Should we deploy to production?"
              ok "Engage"
            }
            steps {
                sh 'serverless deploy --stage prod  --aws-profile prod'
            }
        }
    }
}
