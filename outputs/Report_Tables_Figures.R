# Purpose: generates variable table for report, and figures for variable importance,
# partial plots, and PR and ROC curves for Cross-validation and Independent tests.
#
# Author: David Bucklin
# Created: 2022-05-10

library(readxl)
library(dplyr)
library(stringr)
library(arcgisbinding)
library(ROCR)
library(ggplot2)
library(inlmisc)
arc.check_product()
setwd("D:/git/ConsVision_DevVulnModel/outputs")
# set selected model here.
final.model <- "DevVuln_AllVars_20220510"

# 1. Make Variable table for report
mods <- list.dirs(recursive = F, full.names = F)
mods <- mods[grepl("^DevVuln", mods)]
# Load variable info from models
df.l <- list()
for (m in mods) {
  rd <- paste0(m, "/", m, ".Rdata" )
  if (!file.exists(rd)) {
    print(rd)
    next
  } 
  load(rd)
  pv0 <- names(d)[!names(d) %in% c("y", "class", "sampID", "gridid", "foldid")]
  pv.inc <- row.names(as.data.frame(rf.final$importance))
  pv.exc <- pv0[!pv0 %in% pv.inc]
  
  df <- data.frame(model=m, variable=c(pv.inc, pv.exc), 
                   usage=c(rep("final model", length(pv.inc)), 
                           rep("excluded", length(pv.exc))))  
  df.l[[m]] <- df
}
rm(list=ls()[!ls() %in% c("final.model", "df.l")])
all.mods <- do.call("rbind", df.l)
table(all.mods$model)

# get final variables used
final.vars <- all.mods$variable[all.mods$usage=="final model" & all.mods$model==final.model]

# Load master table
file.vartable <- paste0("../inputs/vars/vars_DV.xlsx")
vars <- read_excel(file.vartable)

# Subset table, make table for report
vars.considered <- unique(all.mods$variable)
length(vars.considered)
vars.used <- vars %>% filter(varname %in% vars.considered) %>% 
  mutate(Static = ifelse(static == 1, "Static", ifelse(multi == 1, "Dynamic, multi-temporal", "Dynamic")), 
         use = ifelse(varname %in% final.vars, "Yes", "No")) %>%
  select(Spatial_Focus = spatial_focus, Variable_Name = varname, Units = units, Calculation_Time_Period = Static,
         Description = description, Short_Description = short_description, 
         Data_Sources = data_sources, Used_in_Final_Model = use) %>% 
  arrange(desc(Used_in_Final_Model), Spatial_Focus, Variable_Name)
nrow(vars.used)
write.csv(vars.used, "report/PredictorVariables_forReport.csv", row.names = F)

# 2. Cross-tables (model x variables)
# write cross-table of 'final model' used variables
a2 <- all.mods %>% filter(usage == "final model")
message("Variables selected, but not present in a 'final' model: " , paste(vars.considered[!vars.considered %in% unique(a2$variable)], collapse = ", "))
vars.crosstab <- as.data.frame.matrix(table(a2$variable, a2$model))
vars.crosstab <- vars.crosstab[names(vars.crosstab)[order(stringr::str_sub(names(vars.crosstab), -8))]]  # arrange according to datestamp
write.csv(vars.crosstab, "report/DV_model_vars_crosstab.csv", row.names = T)

# write cross-table of all-considered variables by model
a2 <- all.mods
vars.crosstab <- as.data.frame.matrix(table(a2$variable, a2$model))
vars.crosstab <- vars.crosstab[names(vars.crosstab)[order(stringr::str_sub(names(vars.crosstab), -8))]] 
write.csv(vars.crosstab, "report/DV_model_vars_crosstab_all_considered.csv", row.names = T)

# Check if there are any duplicate models using exact same variable set (there were not)
mats <- list()
nms <- names(vars.crosstab)
for (n in names(vars.crosstab)) {
  other <- vars.crosstab[nms[!nms %in% n]]
  for (i in 1:length(names(other))) if (all(other[,i] == vars.crosstab[,n])) mats[[length(mats) + 1]] <- sort(c(n, names(other)[i]))
}
unique(mats)
# these variable rasters were developed, but never used in a 'DevVuln' model
vars.neverused <- vars %>% filter(!varname %in% vars.considered)
message("Variables never used in a model: ", paste(vars.neverused$varname, collapse = ", "))


# 3. Figures
pdir <- paste0("report/", final.model, "_plots")
dir.create(pdir)
file.vartable <- paste0("../inputs/vars/vars_DV.xlsx")
vars.master <- read_excel(file.vartable)

# Load model data
m <- paste0(final.model, '/', final.model, ".Rdata")
load(m)

## Variable Importance
imp <- left_join(imp.final, vars.master, by=c("var" = "varname"))
p <- ggplot(imp) + geom_bar(aes(x=reorder(short_description, MeanDecreaseAccuracy), y = MeanDecreaseAccuracy), stat = "identity", position = "dodge") +
  theme_bw() + theme(axis.text.x = element_text(angle = 90, hjust = 1, vjust = -0.1), text = element_text(size = 10)) + 
  coord_flip() + xlab(NULL) + ylab("\nMean Decrease in Accuracy")
p
ggsave(filename = paste0(pdir, "/", "finalModel_varImp.png"), p, height = 4.5, width = 7.5)


## Partial plots 
# make data frame from pPlots, subsets data by 99th percentile of values for class 1. This trims right side of plots.
pp0 <- lapply(seq_along(pPlots), function(x) {
  max.x <- quantile(d[,pPlots[[x]]$varName][d$y == 1],probs = 0.99)[[1]]
  sub <- pPlots[[x]]$x <= max.x
  data.frame(varname=pPlots[[x]]$varName, x=pPlots[[x]]$x[sub], y=pPlots[[x]]$y[sub], rank=as.integer(names(pPlots)[[x]]))
})
pp1 <- left_join(do.call("rbind", pp0), vars.master[c("varname", "short_description")])
pp1$label <- paste0(LETTERS[pp1$rank], ". ", pp1$short_description)

# Facet 
p <- ggplot(pp1 %>% filter(rank <= 6)) + geom_line(aes(x, y)) + facet_wrap(nrow=4, vars(label), scales = "free_x") +
  theme_bw() + xlab("\nVariable Value") + ylab("Log of Fraction of Votes\n") +
  theme(panel.spacing.x = unit(1.5, "lines"))
p
ggsave(filename = paste0(pdir, "/", "pPlots.png"), p, height = 8, width = 7)


## CV curves
# Function to add labeled points to plot
add_labeled_pts <- function(perf, pts, pch=4, lwd=2, cex=1, off.x = 0.1, off.y = -0.05) {
  pt.df <- data.frame(x=NA, y=NA, label=pts)
  for (i in 1:nrow(pt.df)) {
    v <- which.min(abs(perf@alpha.values[[1]] - pt.df$label[i]))
    pt.df$x[i] <- perf@x.values[[1]][v]
    pt.df$y[i] <- perf@y.values[[1]][v]
  } 
  lim <- par("usr")
  ox <- (lim[2] - lim[1]) * off.x
  oy <- (lim[4] - lim[3]) * off.y
  for (i in 1:nrow(pt.df)) {
    pd <- pt.df[i,]
    points(pd$x, pd$y, pch = pch, cex = cex, lwd = lwd)
    text(pd$x+ox, pd$y+oy, pd$label, cex = cex)
    lines(x=c(pd$x+ox*0.2, pd$x+ox-ox*0.35), y = c(pd$y+oy*0.2, pd$y+oy-oy*0.35), lwd = lwd)
  }
}

# Make prediction object
p.rocr <- prediction(df.cv.full$pred, df.cv.full$y)
aucpr <- performance(p.rocr, "aucpr")@y.values[[1]]
aucroc <- performance(p.rocr, "auc")@y.values[[1]]
# Make an adjusted curve for PR, which removes some of the noise on the left side of the plot
p10 <- sort(df.cv.full$pred[df.cv.full$y==1], decreasing = T)[10]
p.rocr.adj <- prediction(df.cv.full[df.cv.full$pred <= p10,]$pred, df.cv.full[df.cv.full$pred <= p10,]$y)

# Settings
r.text <- "Prediction Threshold Value"
# create palette function based on map colors
palf <- colorRampPalette(c(rgb(38,115,0,1, maxColorValue = 255), rgb(245,245,122,1, maxColorValue = 255), rgb(230,76,0,1, maxColorValue = 255)))
pal <- palf(256)
# # Points to add to curves
pt <- 0.5  # seq(0, 1, 0.1)

# P-R curve
perf <- performance(p.rocr.adj, "prec", "rec")
# minx <- 0
png(paste0(pdir, "/", "crossValid_prCurve.png"), width = 5, height = 5, units = "in", res = 240)
par(mar = c(4.1, 4, 1, 1), cex.axis = 1.1, cex.lab=1.1, cex.main = 1.5) # xpd = F
plot(perf, colorize=T, colorize.palette=pal, colorkey = F, ylim=c(0,1)) # xlim = c(minx, 1), xaxs = 'i')
for (i in 1:10) {
  pi <- prediction(df.cv.full$pred[df.cv.full$foldid==i], df.cv.full$y[df.cv.full$foldid==i])
  pip <- performance(pi, "prec", "rec")
  plot(pip, col="grey70", add = T, lwd = 1)
}
baseline <- sum(df.cv.full$y==1) / nrow(df.cv.full)
lines(x=c(0, 1), y = c(baseline, baseline), lty="dashed")
plot(perf, colorize=TRUE, colorize.palette=pal, add = T, lwd = 5) #  print.cutoffs.at = pt)
# legend(x=0.05, y=0.3, legend=c("10% Sample Curves", "Composite Curve"),
#        col=c("grey60", palf(1)), lwd=c(1.5, 4), cex=1, bty = "n")
add_labeled_pts(perf, pt, off.x = -0.1, off.y = -0.05)
AddGradientLegend(seq(0, 1, 0.01), pal=palf, title = "Prediction \nThreshold Value", loc = "bottomleft", inset = c(0.8, 0.6), strip.dim = c(1.5, 5))
text(0.15, 0.12, labels=paste0("AUC(PRC) = ", round(aucpr, 3)), adj=0, cex = 1)
dev.off()

# ROC curve
perf <- performance(p.rocr, "tpr", "fpr")
png(paste0(pdir, "/", "crossValid_rocCurve.png"), width = 5, height = 5, units = "in", res = 240)
par(mar = c(4.1, 4, 1, 1), cex.axis = 1.1, cex.lab=1.1, cex.main = 1.5)
plot(perf, colorize=T, colorize.palette=pal, ylim = c(0, 1), 
     colorkey = F)
for (i in 1:10) {
  pi <- prediction(df.cv.full$pred[df.cv.full$foldid==i], df.cv.full$y[df.cv.full$foldid==i])
  pip <- performance(pi, "tpr", "fpr")
  plot(pip, col="grey70", add = T, lwd = 1)
}
lines(x=c(0, 1), y = c(0, 1), lty="dashed")
plot(perf, colorize=T, colorize.palette=pal, add = T, lwd = 5)
add_labeled_pts(perf, pt)
# legend(0.4, 0.3, legend=c("10% Sample Curves", "Composite Curve"),
#       col=c("grey60", palf(1)), lwd=c(1.5, 4), cex=1, bty = "n")
text(0.5, 0.12, labels=paste0("AUC(ROC) = ", round(aucroc, 3)), adj=0, cex = 1)
AddGradientLegend(seq(0, 1, 0.01), pal=palf, title = "Prediction \nThreshold Value", loc = "bottomleft", inset = c(0.8, 0.3), strip.dim = c(1.5, 5))
dev.off()


## Independent test data curves
rm(perf, d, p.rocr, aucpr, aucroc)
# load points 
test.pts <- paste0("samples_validation.gdb/", proj.mod, "_indpValidRaw_pts")
v1 <- arc.select(arc.open(test.pts))
p.rocr <- prediction(v1$pred, v1$y)
aucpr <- performance(p.rocr, "aucpr")@y.values[[1]]
aucroc <- performance(p.rocr, "auc")@y.values[[1]]
# Make an adjusted curve for PR, which removes some of the noise on the left side of the plot
p10 <- sort(v1$pred[v1$y==1], decreasing = T)[10]
p.rocr.adj <- prediction(v1[v1$pred <= p10,]$pred, v1[v1$pred <= p10,]$y)

# P-R curve
perf <- performance(p.rocr.adj, "prec", "rec")
png(paste0(pdir, "/", "indpTest_prCurve.png"), width = 5, height = 5, units = "in", res = 240)
par(mar = c(4.1, 4, 1, 1), cex.axis = 1.1, cex.lab=1.1, cex.main = 1.5)
plot(perf, colorize=T, colorize.palette=pal, colorkey = F, ylim=c(0, 1)) # , xlim = c(minx, 1), xaxs = 'i')
baseline <- sum(v1$y==1) / nrow(v1)
lines(x=c(0, 1), y = c(baseline, baseline), lty="dashed")
plot(perf, colorize=TRUE, colorize.palette=pal, add = T, lwd = 5)
add_labeled_pts(perf, pt, off.x = -0.1, off.y = -0.05)
AddGradientLegend(seq(0, 1, 0.01), pal=palf, title = "Prediction \nThreshold Value", loc = "bottomleft", inset = c(0.8, 0.6), strip.dim = c(1.5, 5))
text(0.15, 0.12, labels=paste0("AUC(PRC) = ", round(aucpr, 3)), adj=0, cex = 1)
dev.off()

# ROC curve
perf <- performance(p.rocr, "tpr", "fpr")
png(paste0(pdir, "/", "indpTest_rocCurve.png"), width = 5, height = 5, units = "in", res = 240)
par(mar = c(4.1, 4, 1, 1), cex.axis = 1.1, cex.lab=1.1, cex.main = 1.5)
plot(perf, colorize=T, colorize.palette=pal, ylim = c(0, 1), colorkey = F)
lines(x=c(0, 1), y = c(0, 1), lty="dashed")
plot(perf, colorize=T, colorize.palette=pal, add = T, lwd = 5)
add_labeled_pts(perf, pt)
text(0.5, 0.12, labels=paste0("AUC(ROC) = ", round(aucroc, 3)), adj=0, cex = 1)
AddGradientLegend(seq(0, 1, 0.01), pal=palf, title = "Prediction \nThreshold Value", loc = "bottomleft", inset = c(0.8, 0.3), strip.dim = c(1.5, 5))
dev.off()

# end
