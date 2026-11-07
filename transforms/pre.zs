;; JIRA arguments_script: Transform plain text into Atlassian Document Format (ADF)
{:fields
 {:summary (clean-text (get input :summary))
  :description {:type "doc"
                :version 1
                :content [{:type "paragraph"
                           :content [{:type "text" :text (clean-text (get input :description))}]}]}
  :issuetype {:name (get input :issueType "Task")}
  :project {:key (clean-name (get input :projectKey))}}}
