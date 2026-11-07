;; JIRA result_script: Project only critical fields, strip avatars and schema bloat
(let [key (get input :key)
      fields (get input :fields)
      summary (get-in fields [:summary])
      status (get-in fields [:status :name])
      assignee (get-in fields [:assignee :displayName] "Unassigned")]
  {:key key
   :summary summary
   :status status
   :assignee assignee})
